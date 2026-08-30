-- =====================================================================================
-- build_all.sql
-- The whole derived-table DAG for the All of Us spine wearable study, as three
-- persistent user-defined functions plus one BigQuery stored procedure.
--
-- WHY THIS IS A STORED PROCEDURE AND NOT A NOTEBOOK CELL
-- Every prior All of Us session in this repo re-materialized parquets from SQL because
-- the workspace had no writable home, and wrote scratch to /tmp, the one location
-- guaranteed to vanish with the compute disk. Compiling the DAG into the CDR's own
-- project means the next session is one CALL against tables that already exist, and a
-- deleted environment costs nothing but the CALL. The procedure is idempotent: every
-- statement is CREATE OR REPLACE, so a re-run overwrites rather than appends.
--
-- WHERE THIS RUNS
-- Inside the perimeter only, submitted by pipeline/03_cohort.py through
-- 00_config.ipynb's q_guarded(), which is the only query path and which carries the
-- maximum_bytes_billed cap. Nothing here prints, returns or exports a row. Every table
-- it writes lives in {DERIVED} and, apart from cs_spine and cs_condition, is
-- participant-level and may never be selected into an export. See DAG-SCHEMA.md.
--
-- PLACEHOLDERS
-- {CDR}      the resolved Controlled Tier CDR dataset, project.dataset
-- {PREP}     the resolved prep CDR dataset, project.dataset. DELIBERATELY UNUSED here;
--            its table inventory is an unconfirmed runtime probe, so nothing in this
--            DAG depends on it.
-- {DERIVED}  the workspace project's own spinewear derived dataset, resolved at
--            runtime by 00_config.ipynb
-- The workspace project name is NOT a placeholder: writing it in braces would leave
-- a residual identifier that 00_config.ipynb's _fill raises on, so it is never
-- written that way anywhere in this file, not even inside a comment.
-- There is no hardcoded project, dataset or bucket anywhere in this file.
--
-- HOW TO PRICE IT BEFORE IT RUNS
-- A dry run of CALL does not price the procedure body. Every stage body is therefore
-- delimited by a marker pair
--     a line reading   @stage-begin   followed by a colon and the table name
--     a line reading   @stage-end     followed by a colon and the same name
-- and every stage body reads its run parameters from {DERIVED}.build_params rather
-- than from procedure variables, so a body lifted out between its markers is
-- standalone-valid SQL that dry-runs on its own. 03_cohort.py splits on those markers,
-- dry-runs each body, and prints the byte estimate for that stage.
--
-- SIZE THE CAP PER STAGE, NOT AGAINST THE DAG TOTAL. maximum_bytes_billed on a
-- BigQuery script is enforced PER CHILD JOB, not across the script. CALL is a script
-- job and each of these 19 stages is a child job the cap is applied to individually, so
-- a cap sized to the 19-stage total permits EACH stage to bill up to that total, which
-- is up to nineteen times the approved number. Give every stage its own max_gb from its
-- own dry-run estimate. The DAG total is an approval figure checked before submission,
-- not a cap; nothing enforces it at run time. The binding stage is expected to be
-- hr_daily, the only scan of heart_rate_summary, with features the one rival because it
-- is the only stage scanning two large CDR tables in a single job. DAG-SCHEMA.md 5.1
-- carries this in full.
--
-- TWO STAGES ARE FORMAT TEMPLATES, NOT ONE: hr_daily AND device_daily. Both are built
-- with EXECUTE IMMEDIATE FORMAT because a column name cannot be a query parameter.
-- 03_cohort.py MUST substitute hr_minute_column into hr_daily's two %s positions and
-- device_model_column into device_daily's one %s BEFORE the dry run. If the
-- substitution is skipped, the dry run prices a query that is not the one that will
-- execute: the estimate is meaningless and the per-stage cap above is sized against the
-- wrong number. device_daily is the one that gets missed, because its template sits on
-- the ELSE branch of the empty-column-name test rather than at the top of the body.
-- Neither template carries a literal percent sign other than those substitutions, so
-- adding one without doubling it would corrupt the statement.
-- Both bodies carry an @stage-format-args line naming their FORMAT arguments in order,
-- inside their own @stage-begin / @stage-end pair, so the requirement is checkable and
-- not merely written down: a body containing EXECUTE IMMEDIATE FORMAT( must carry that
-- line, a body without it must not, the names on the line must number the same as the
-- %s in the template, and no %s may survive substitution. The %s in episodes, events
-- and risk_sets are ordinary FORMAT calls in static SQL and are not templates, which is
-- why the test keys on EXECUTE IMMEDIATE FORMAT( and not on the percent sign.
--
-- HOUSE RULES OBSERVED HERE
-- No em-dash and no U+2212 anywhere in this file. No nondeterministic random ordering:
-- every sample is a seeded FARM_FINGERPRINT. No approximate two-quantile expression
-- standing in for a median, because that form returns the UPPER value on an
-- even-length array and is therefore not a median; see the exact_median UDF below and
-- the self-test in the procedure that proves it. No display string: every printable
-- sentence in this study is owned by LABELS in 07_export.py and local/ledger.py, so
-- this file emits slugs and integers only.
-- Those three prohibitions are also greppable: the banned tokens do not appear in
-- this file at all, not even in a comment explaining why they are banned.
-- =====================================================================================


-- -------------------------------------------------------------------------------------
-- UDF 1 of 4. THE EXACT MEDIAN, AND WHY IT IS A FUNCTION RATHER THAN AN EXPRESSION.
--
-- BigQuery's approximate-quantile function, asked for two quantiles and indexed at
-- offset one, returns the UPPER of the two middle values on an even-length array. The preoperative baseline B_i (ANALYSIS-PLAN 2.2) is defined as a
-- median, and the proximal exposure R_72 (4.2) is a median over a window that carries
-- as few as two valid days, so the even-length case is the ordinary case there, not the
-- edge case. Using the approximate form would bias EVERY baseline and EVERY two-day
-- proximal window upward, in the same direction, invisibly. It is written once, here,
-- so that no downstream query can reintroduce it.
--
-- RETURN ON AN EMPTY ARRAY: NULL, not zero. A participant with no valid baseline day
-- must produce a NULL baseline, because a zero baseline would make the normalized
-- activity S/B infinite and the deficit max(0, 1 - S/B) silently equal to 1 on every
-- day, manufacturing a maximal recovery debt out of an absence of data. NULL propagates
-- and is caught by attrition rung 12. The same holds for an array of all NULLs.
-- Correct for both parities: odd n returns the middle element, even n returns the mean
-- of the two middle elements. SAFE_OFFSET rather than OFFSET so that an unexpected
-- empty array returns NULL instead of raising out of range.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION `{DERIVED}.exact_median`(xs ARRAY<FLOAT64>)
RETURNS FLOAT64
AS ((
  SELECT
    IF(n = 0,
       NULL,
       IF(MOD(n, 2) = 1,
          vals[SAFE_OFFSET(DIV(n, 2))],
          (vals[SAFE_OFFSET(DIV(n, 2) - 1)] + vals[SAFE_OFFSET(DIV(n, 2))]) / 2))
  FROM (
    SELECT ARRAY_AGG(v ORDER BY v) AS vals, COUNT(v) AS n
    FROM UNNEST(xs) AS v
    WHERE v IS NOT NULL
  )
));


-- -------------------------------------------------------------------------------------
-- UDF 2 of 4. The same median over an INT64 array, so that a caller aggregating a step
-- count never has to write a cast and never has to reach for the approximate form
-- because the types did not line up. Returns FLOAT64 because the even-length median of two
-- integers is not in general an integer.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION `{DERIVED}.exact_median_int`(xs ARRAY<INT64>)
RETURNS FLOAT64
AS ((
  SELECT `{DERIVED}.exact_median`(ARRAY(SELECT CAST(v AS FLOAT64) FROM UNNEST(xs) AS v WHERE v IS NOT NULL))
));


-- -------------------------------------------------------------------------------------
-- UDF 3 of 4. The five valid-wear-day definitions of ANALYSIS-PLAN 2.1, in one place.
-- The wear rule decides what counts as a missing day, so it decides the primary
-- estimator's whole exposure to missingness; four of the fourteen plotted sensitivity
-- rows vary nothing else. Writing the five thresholds once means a sensitivity row and
-- the primary cannot drift apart by a transcription slip.
--   'primary'  at least 600 heart-rate minutes
--   's1'       at least 40% daily heart-rate adherence, which is 576 of 1,440 minutes
--   's2'       at least 10 hours of heart-rate wear AND at least 100 steps
--   's3'       at least 8 hours
--   's4'       at least 12 hours
-- A NULL wear_minutes means no heart_rate_summary row for that person-date, which is
-- not the same claim as zero minutes, and it is never a valid day under any definition.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION `{DERIVED}.is_valid_wear`(wear_minutes INT64, steps INT64, definition STRING)
RETURNS BOOL
AS ((
  SELECT CASE definition
           WHEN 'primary' THEN IFNULL(wear_minutes, -1) >= 600
           WHEN 's1'      THEN IFNULL(wear_minutes, -1) >= 576
           WHEN 's2'      THEN IFNULL(wear_minutes, -1) >= 600 AND IFNULL(steps, -1) >= 100
           WHEN 's3'      THEN IFNULL(wear_minutes, -1) >= 480
           WHEN 's4'      THEN IFNULL(wear_minutes, -1) >= 720
           ELSE NULL
         END
));


-- -------------------------------------------------------------------------------------
-- UDF 4 of 4. The device model-family rule of ANALYSIS-PLAN 3.6, which was the one cell
-- of the locked covariate table an analyst could still decide after seeing the data.
-- Mechanical and prespecified: uppercase the model string, take the first run of
-- letters, and accept it only if it is one of the fourteen fixed family names.
-- Generation is deliberately not distinguished, because generation is largely a proxy
-- for calendar year, which is already in the model, and splitting on it would
-- manufacture thin levels that the disclosure-floor folding rule would immediately
-- re-merge on the basis of observed counts, which is exactly the data-dependent choice
-- this rule removes. A NULL, an empty string or an unrecognised token returns
-- 'other_or_unknown', which is a level and not a missing value.
-- Emits a slug, never a display string: 07_export.py renders the printable label.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION `{DERIVED}.device_family`(model STRING)
RETURNS STRING
AS ((
  SELECT IFNULL(
    (SELECT LOWER(tok)
     FROM UNNEST([REGEXP_EXTRACT(UPPER(IFNULL(model, '')), r'[A-Z]+')]) AS tok
     WHERE tok IN ('CHARGE','VERSA','SENSE','INSPIRE','LUXE','ALTA','IONIC','BLAZE',
                   'SURGE','FLEX','ONE','ZIP','ACE','ULTRA')),
    'other_or_unknown')
));


-- =====================================================================================
-- THE PROCEDURE
--
-- CALL `{DERIVED}.build_all`(
--        junction_map              => 'primary',            -- or 'mirrored'
--        hr_minute_column          => 'minute_in_zone',     -- PROBED by 01_probe.py
--        device_model_column       => 'device_version',     -- PROBED, '' if unavailable
--        ed_visit_concept_ids      => [9203, 262],          -- ENUMERATED by 01_probe.py
--        inpatient_visit_concept_ids => [9201, 262],        -- ENUMERATED by 01_probe.py
--        primary_wear_definition   => 'primary',            -- or 's2' under the 2.1 fallback
--        start_stage               => '');                  -- '' builds everything
--
-- Named arguments are shown for readability; BigQuery CALL takes them positionally, so
-- 03_cohort.py passes them in the declared order. The values above are ILLUSTRATIVE.
-- Three of them are runtime probes and none of them is a constant of this study:
--   hr_minute_column      the per-zone minute column of heart_rate_summary. Summing it
--                         gives the wear figure at roughly four rows per person-day
--                         against 1,440 for the minute-level table, which is the single
--                         fact that keeps this project under two dollars.
--   device_model_column   the model string column of the device table.
--   ed/inpatient ids      enumerated against the CDR's own visit_concept_id
--                         distribution (ANALYSIS-PLAN 4.1), never assumed.
-- Each is validated below and RAISES if it does not resolve, so a wrong probe result
-- stops the build rather than producing a table of zeroes that looks like a finding.
-- =====================================================================================
CREATE OR REPLACE PROCEDURE `{DERIVED}.build_all`(
  junction_map STRING,
  hr_minute_column STRING,
  device_model_column STRING,
  ed_visit_concept_ids ARRAY<INT64>,
  inpatient_visit_concept_ids ARRAY<INT64>,
  primary_wear_definition STRING,
  start_stage STRING
)
BEGIN
  -- All DECLAREs precede every other statement, as BigQuery scripting requires.
  -- THE DAG ORDER. The index of a name here is the number its stage guard compares
  -- start_ix against, so this array and the IF start_ix <= N guards below must stay in
  -- step. DAG-SCHEMA.md carries the same order and the same numbers.
  DECLARE stages ARRAY<STRING> DEFAULT [
    'build_params',                   --  1
    'cs_spine',                       --  2
    'cs_condition',                   --  3
    'episodes',                       --  4
    'hr_daily',                       --  5
    'device_daily',                   --  6
    'fitbit_daily',                   --  7
    'baseline',                       --  8
    'episodes_eligible',              --  9
    'features',                       -- 10
    'drd_daily',                      -- 11
    'events',                         -- 12
    'landmark_daily',                 -- 13
    'risk_sets',                      -- 14
    'attrition',                      -- 15
    'ledger_exclusion_reasons',       -- 16
    'ledger_wear_by_day',             -- 17
    'ledger_matched_sets',            -- 18
    'ledger_variable_missingness'     -- 19
  ];
  DECLARE start_ix INT64 DEFAULT 1;
  DECLARE zone_overflow_days INT64 DEFAULT 0;
  DECLARE ladder_breaks INT64 DEFAULT 0;

  -- The seed and the sampling salt are NOT parameters. ANALYSIS-PLAN 4.5 and 10 pin
  -- SEED = 0, and a knob that can only break reproducibility is worse than no knob.
  DECLARE seed INT64 DEFAULT 0;
  DECLARE sampling_salt STRING DEFAULT 'spinewear-v1-risk-set';

  -- ---------------------------------------------------------------------------------
  -- PARAMETER VALIDATION. Each of these is a stop condition, not a warning.
  -- ---------------------------------------------------------------------------------
  IF junction_map NOT IN ('primary', 'mirrored') THEN
    RAISE USING MESSAGE = 'junction_map must be primary or mirrored. Under the mirrored map the stems 0RG4 and 0RB5 become thoracic, so an episode whose only evidence is cervicothoracic moves from cervical to thoracic-only, that is from included to excluded, and the two runs legitimately produce different ladders.';
  END IF;

  IF primary_wear_definition NOT IN ('primary', 's2') THEN
    RAISE USING MESSAGE = 'primary_wear_definition must be primary, or s2 under the prespecified contingency of ANALYSIS-PLAN 2.1, which is invoked only when the zone-partition probe fails and the substitution is logged as an amendment.';
  END IF;

  -- The column names are interpolated into dynamic SQL, so they are shape-checked
  -- before they are ever concatenated. An identifier regex is the whole defence.
  IF NOT REGEXP_CONTAINS(hr_minute_column, r'^[A-Za-z_][A-Za-z0-9_]*$') THEN
    RAISE USING MESSAGE = 'hr_minute_column is not a bare SQL identifier. It is interpolated into dynamic SQL and is refused unless it matches ^[A-Za-z_][A-Za-z0-9_]*$.';
  END IF;

  IF device_model_column != '' AND NOT REGEXP_CONTAINS(device_model_column, r'^[A-Za-z_][A-Za-z0-9_]*$') THEN
    RAISE USING MESSAGE = 'device_model_column is not a bare SQL identifier. Pass the empty string when the device table carries no usable model column, in which case every episode takes device family other_or_unknown and features.device_family_source records that it did.';
  END IF;

  IF ARRAY_LENGTH(ed_visit_concept_ids) = 0 OR ARRAY_LENGTH(inpatient_visit_concept_ids) = 0 THEN
    RAISE USING MESSAGE = 'ed_visit_concept_ids and inpatient_visit_concept_ids are both required and neither may be empty. They are enumerated against the CDR visit_concept_id distribution by 01_probe.py (ANALYSIS-PLAN 4.1). An empty array would silently make every acute-care event and every emergency-department exclusion count zero.';
  END IF;

  -- LOUD FAILURE IF THE PROBED WEAR COLUMN IS ABSENT. Without this check the SUM would
  -- resolve against nothing, the build would succeed, and every wear minute in the
  -- study would be zero, which reads as total non-wear rather than as a broken probe.
  -- INFORMATION_SCHEMA is metadata and bills nothing.
  IF (SELECT COUNT(*)
      FROM `{CDR}.INFORMATION_SCHEMA.COLUMNS`
      WHERE table_name = 'heart_rate_summary'
        AND column_name IN (hr_minute_column, 'person_id', 'date')) != 3 THEN
    RAISE USING MESSAGE = 'heart_rate_summary does not carry all three of person_id, date and the probed per-zone minute column. Re-run 01_probe.py and pass the column name it reports. Refusing to build rather than summing a column that is not there and reporting zero wear minutes for the whole cohort.';
  END IF;

  IF device_model_column != ''
     AND (SELECT COUNT(*)
          FROM `{CDR}.INFORMATION_SCHEMA.COLUMNS`
          WHERE table_name = 'device' AND column_name = device_model_column) = 0 THEN
    RAISE USING MESSAGE = 'The named device model column does not exist on the device table. Pass the empty string to build without a device covariate, or pass the name 01_probe.py reports.';
  END IF;

  -- THE UDF SELF-TEST. This is the assertion that the median is a median. On the
  -- even-length array below, the approximate two-quantile form returns 4.0; a true
  -- median returns 3.0. If this line ever fails, the UDF has been replaced by the
  -- approximate form and every baseline in the study is biased upward.
  ASSERT `{DERIVED}.exact_median`([1.0, 2.0, 4.0, 8.0]) = 3.0
    AS 'exact_median is wrong on an even-length array';
  ASSERT `{DERIVED}.exact_median`([1.0, 2.0, 4.0]) = 2.0
    AS 'exact_median is wrong on an odd-length array';
  ASSERT `{DERIVED}.exact_median`(ARRAY<FLOAT64>[]) IS NULL
    AS 'exact_median must return NULL on an empty array, never zero';
  ASSERT `{DERIVED}.exact_median_int`([1, 2, 4, 8]) = 3.0
    AS 'exact_median_int is wrong on an even-length array';
  ASSERT `{DERIVED}.device_family`('Fitbit Charge 5') = 'charge'
    AS 'device_family must take the first run of letters and ignore generation';
  ASSERT `{DERIVED}.device_family`(NULL) = 'other_or_unknown'
    AS 'device_family must map a null model string to a level, not to a null';
  ASSERT `{DERIVED}.is_valid_wear`(600, 0, 'primary')
     AND NOT `{DERIVED}.is_valid_wear`(599, 99999, 'primary')
     AND NOT `{DERIVED}.is_valid_wear`(NULL, 5000, 'primary')
    AS 'is_valid_wear does not implement the primary 600-minute rule';

  -- Resume support. start_stage names the FIRST stage to rebuild; everything before it
  -- is left as it stands from the previous session. build_params is always rewritten,
  -- because it is the record of what this run was called with.
  IF start_stage != '' THEN
    SET start_ix = IFNULL(
      (SELECT off + 1 FROM UNNEST(stages) AS s WITH OFFSET off WHERE s = start_stage),
      0);
    IF start_ix = 0 THEN
      RAISE USING MESSAGE = 'start_stage is not a stage name. Pass the empty string to build everything, or one of the nineteen table names in DAG-SCHEMA.md, in DAG order.';
    END IF;
  END IF;

  -- ===================================================================================
  -- STAGE 1 of 19: build_params
  -- The run's parameters, materialized as one row so that every later stage body reads
  -- them from a table instead of from a procedure variable. That is what makes each
  -- stage body standalone-valid SQL and therefore dry-runnable and priceable on its own
  -- before the CALL. It is also the provenance record: the ladder, and every table that
  -- carries junction_map, can be traced back to the map and the probes that produced it.
  -- This is the ONE stage whose body cannot be lifted out for a dry run, because it is
  -- the stage that turns procedure variables into a table. It scans one column of
  -- observation_period and nothing else.
  -- ===================================================================================
  -- @stage-begin: build_params
  CREATE OR REPLACE TABLE `{DERIVED}.build_params` AS
  SELECT
    junction_map                    AS junction_map,
    hr_minute_column                AS hr_minute_column,
    device_model_column             AS device_model_column,
    ed_visit_concept_ids            AS ed_visit_concept_ids,
    inpatient_visit_concept_ids     AS inpatient_visit_concept_ids,
    primary_wear_definition         AS primary_wear_definition,
    seed                            AS seed,
    sampling_salt                   AS sampling_salt,
    CURRENT_TIMESTAMP()             AS built_at,
    (SELECT MAX(observation_period_end_date) FROM `{CDR}.observation_period`)
                                    AS cdr_observation_cutoff;
  -- @stage-end: build_params

  -- ===================================================================================
  -- STAGE 2 of 19: cs_spine
  -- The locked 852-concept spine set, region-tagged, transcribed from
  -- pipeline/cs_spine.py. Both region assignments are carried on every row
  -- unconditionally, so a row where they differ IS a junction code and needs no flag
  -- beyond is_junction, and so the mirrored sensitivity does not need a second table.
  -- The effective region for THIS run is resolved once, here, from build_params.
  -- Grain: one row per concept_id. Roughly 852 rows.
  -- Vocabulary metadata, not participant data: this table and cs_condition are the only
  -- two in {DERIVED} that carry no participant-level column.
  -- ===================================================================================
  IF start_ix <= 2 THEN
  -- @stage-begin: cs_spine
  CREATE OR REPLACE TABLE `{DERIVED}.cs_spine` AS
  WITH p AS (SELECT junction_map FROM `{DERIVED}.build_params`),
  src AS (
    SELECT
      c.concept_id,
      c.vocabulary_id,
      c.concept_code,
      c.concept_name,
      IF(c.vocabulary_id = 'CPT4', 'exact', 'stem4') AS match_kind,
      CASE
        WHEN c.vocabulary_id = 'CPT4' AND c.concept_code IN ('22551','22600','63020','63075') THEN 'cervical'
        WHEN c.vocabulary_id = 'CPT4' AND c.concept_code IN ('22610') THEN 'thoracic'
        WHEN c.vocabulary_id = 'CPT4' AND c.concept_code IN ('22558','22612','22630','22633','63005','63012','63017','63030','63047') THEN 'lumbar'
        WHEN c.vocabulary_id = 'CPT4' THEN 'unspecified'
        WHEN SUBSTR(c.concept_code, 1, 4) IN ('00NW','0RB3','0RB5','0RG0','0RG1','0RG2','0RG4') THEN 'cervical'
        WHEN SUBSTR(c.concept_code, 1, 4) IN ('00NX','0RB9','0RBB','0RG6','0RG7','0RG8','0RGA') THEN 'thoracic'
        WHEN SUBSTR(c.concept_code, 1, 4) IN ('00NY','0SB2','0SB4','0SG0','0SG1','0SG3') THEN 'lumbar'
        ELSE 'unspecified'
      END AS region_primary,
      -- The mirrored map sends each junction stem to the CAUDAL member instead of the
      -- cranial one: 0RG4 and 0RB5 cervicothoracic become thoracic, 0RGA and 0RBB
      -- thoracolumbar become lumbar. 00NT stays unspecified under both maps, because
      -- its fourth character names a tissue rather than a level and no sensitivity can
      -- recover a level that was never coded.
      CASE
        WHEN c.vocabulary_id = 'CPT4' AND c.concept_code IN ('22551','22600','63020','63075') THEN 'cervical'
        WHEN c.vocabulary_id = 'CPT4' AND c.concept_code IN ('22610') THEN 'thoracic'
        WHEN c.vocabulary_id = 'CPT4' AND c.concept_code IN ('22558','22612','22630','22633','63005','63012','63017','63030','63047') THEN 'lumbar'
        WHEN c.vocabulary_id = 'CPT4' THEN 'unspecified'
        WHEN SUBSTR(c.concept_code, 1, 4) IN ('00NW','0RB3','0RG0','0RG1','0RG2') THEN 'cervical'
        WHEN SUBSTR(c.concept_code, 1, 4) IN ('00NX','0RB5','0RB9','0RG4','0RG6','0RG7','0RG8') THEN 'thoracic'
        WHEN SUBSTR(c.concept_code, 1, 4) IN ('00NY','0RBB','0RGA','0SB2','0SB4','0SG0','0SG1','0SG3') THEN 'lumbar'
        ELSE 'unspecified'
      END AS region_mirrored,
      CASE
        WHEN c.vocabulary_id = 'CPT4'
             AND c.concept_code IN ('63005','63012','63017','63020','63030','63035','63047','63048','63075') THEN 'decompression'
        WHEN c.vocabulary_id = 'CPT4' THEN 'fusion'
        WHEN SUBSTR(c.concept_code, 1, 4) IN ('00NT','00NW','00NX','00NY','0RB3','0RB5','0RB9','0RBB','0SB2','0SB4') THEN 'decompression'
        ELSE 'fusion'
      END AS procedure_class,
      -- Sixteen of the thirty CPT-4 concepts are add-on or instrumentation codes and
      -- cannot define an operation on their own. No ICD-10-PCS stem in the locked set
      -- is an add-on.
      (c.vocabulary_id = 'CPT4'
       AND c.concept_code IN ('22614','22632','22634','22840','22841','22842','22843','22844',
                              '22845','22846','22847','22848','22853','22854','63035','63048')) AS is_add_on
    FROM `{CDR}.concept` AS c
    WHERE (c.vocabulary_id = 'CPT4'
           AND c.concept_code IN ('22551','22558','22600','22610','22612','22614','22630','22632',
                                  '22633','22634','22840','22841','22842','22843','22844','22845',
                                  '22846','22847','22848','22853','22854','63005','63012','63017',
                                  '63020','63030','63035','63047','63048','63075'))
       OR (c.vocabulary_id = 'ICD10PCS'
           AND SUBSTR(c.concept_code, 1, 4) IN ('00NT','00NW','00NX','00NY','0RB3','0RB5','0RB9',
                                                '0RBB','0RG0','0RG1','0RG2','0RG4','0RG6','0RG7',
                                                '0RG8','0RGA','0SB2','0SB4','0SG0','0SG1','0SG3'))
  )
  SELECT
    src.concept_id,
    src.vocabulary_id,
    src.concept_code,
    src.concept_name,
    src.match_kind,
    src.region_primary,
    src.region_mirrored,
    IF(p.junction_map = 'mirrored', src.region_mirrored, src.region_primary) AS region,
    src.procedure_class,
    src.is_add_on,
    (src.region_primary != src.region_mirrored) AS is_junction,
    p.junction_map
  FROM src CROSS JOIN p;
  -- @stage-end: cs_spine

  -- A different concept count means the CDR vocabulary changed under us and every
  -- count downstream is suspect. The locked set is 852 concepts: 30 CPT-4 plus 704
  -- ICD-10-PCS fusion plus 118 ICD-10-PCS decompression.
  IF (SELECT COUNT(*) FROM `{DERIVED}.cs_spine`) != 852 THEN
    RAISE USING MESSAGE = 'The locked spine concept set did not resolve to 852 concepts against this CDR. Stop and reconcile pipeline/cs_spine.py against the CDR concept table before any count is read.';
  END IF;
  END IF;

  -- ===================================================================================
  -- STAGE 3 of 19: cs_condition
  -- Every condition concept set the DAG needs, in one auditable table: the composite
  -- nonelective-indication screen of attrition rung 3, the degenerative-spine set that
  -- rescues an episode at rung 4, and the Quan ICD-10 mapping for the Charlson index.
  -- Materializing it means the features stage joins a small table instead of running a
  -- regular expression against the condition records, and it means a reviewer can read
  -- the exclusion vocabulary rather than reconstruct it from a WHERE clause.
  --
  -- Matching is on concept_code with ICD-10-CM only, joined downstream on
  -- condition_source_concept_id, which is the same source-code path the locked spine
  -- concept set uses. KNOWN AND ACCEPTED GAP: ICD-9-CM coded conditions are not
  -- screened. The study window is the Fitbit era, so pre-2015 records are a small and
  -- shrinking share, and adding ICD-9 would double the vocabulary for episodes whose
  -- wearable data does not exist. Stated in DAG-SCHEMA.md rather than left to be found.
  --
  -- Grain: one row per concept per category. A concept may appear under more than one
  -- category, which is intended: malignancy is both a nonelective indication and a
  -- Charlson category, and the two are counted by different consumers.
  -- Roughly 40,000 rows. Vocabulary metadata, no participant-level column.
  -- ===================================================================================
  IF start_ix <= 3 THEN
  -- @stage-begin: cs_condition
  CREATE OR REPLACE TABLE `{DERIVED}.cs_condition` AS
  WITH pat AS (
    SELECT * FROM UNNEST([
      -- The composite screen of rung 3. One rung, not three, because a ladder counts
      -- each episode once at the first rung it fails and an episode can trip more than
      -- one indication at a time; three rungs would carry order-dependent counts that
      -- read as prevalences. The per-indication breakdown goes to
      -- ledger_exclusion_reasons, where rows may overlap and are not a partition.
      STRUCT('nonelective_indication' AS category_kind, 'trauma' AS category,
             CAST(NULL AS INT64) AS weight,
             r'^(S12|S13|S22|S23|S32|S33|T08|T09|M48\.4|M48\.5)' AS pattern),
      STRUCT('nonelective_indication', 'spinal_cord_injury', NULL,
             r'^(S14|S24|S34|G95\.1|T09\.3)'),
      STRUCT('nonelective_indication', 'malignancy', NULL,
             r'^(C[0-6][0-9]|C7[0-6]|C8[0-9]|C9[0-7]|D46|D47\.Z)'),
      STRUCT('nonelective_indication', 'metastatic_disease', NULL,
             r'^(C77|C78|C79|C7B|C80)'),
      STRUCT('nonelective_indication', 'spinal_infection', NULL,
             r'^(M46\.2|M46\.3|M46\.4|M46\.5|G06\.1|G06\.2|M49\.0|A18\.0)'),

      -- The degenerative index diagnoses that rescue an episode at rung 4: spondylosis,
      -- spinal stenosis, disc degeneration or displacement, spondylolisthesis, and
      -- radiculopathy. Myelopathy of degenerative origin lives inside M47 and M50, so
      -- it needs no separate stem.
      STRUCT('degenerative_spine', 'degenerative_spine', NULL,
             r'^(M47|M48\.0|M50|M51|M43\.1|M54\.1)'),

      -- Quan ICD-10 mapping, Charlson weights. The hierarchy rules (metastatic
      -- supersedes any malignancy, moderate or severe liver supersedes mild, diabetes
      -- with complication supersedes without) are applied in the features stage, not
      -- here, because they are a scoring rule and not a vocabulary fact.
      STRUCT('charlson', 'myocardial_infarction', 1, r'^(I21|I22|I25\.2)'),
      STRUCT('charlson', 'congestive_heart_failure', 1,
             r'^(I09\.9|I11\.0|I13\.0|I13\.2|I25\.5|I42\.0|I42\.[5-9]|I43|I50|P29\.0)'),
      STRUCT('charlson', 'peripheral_vascular_disease', 1,
             r'^(I70|I71|I73\.1|I73\.8|I73\.9|I77\.1|I79\.0|I79\.2|K55\.1|K55\.8|K55\.9|Z95\.8|Z95\.9)'),
      STRUCT('charlson', 'cerebrovascular_disease', 1, r'^(G45|G46|H34\.0|I6[0-9])'),
      STRUCT('charlson', 'dementia', 1, r'^(F0[0-3]|F05\.1|G30|G31\.1)'),
      STRUCT('charlson', 'chronic_pulmonary_disease', 1,
             r'^(I27\.8|I27\.9|J4[0-7]|J6[0-7]|J68\.4|J70\.1|J70\.3)'),
      STRUCT('charlson', 'rheumatic_disease', 1,
             r'^(M05|M06|M31\.5|M3[2-4]|M35\.1|M35\.3|M36\.0)'),
      STRUCT('charlson', 'peptic_ulcer_disease', 1, r'^K2[5-8]'),
      STRUCT('charlson', 'mild_liver_disease', 1,
             r'^(B18|K70\.[0-39]|K71\.[3-57]|K73|K74|K76\.0|K76\.[2-489]|Z94\.4)'),
      STRUCT('charlson', 'diabetes_without_complication', 1, r'^E1[0-4]\.[01689]'),
      STRUCT('charlson', 'diabetes_with_complication', 2, r'^E1[0-4]\.[2-57]'),
      STRUCT('charlson', 'hemiplegia_or_paraplegia', 2,
             r'^(G04\.1|G11\.4|G80\.1|G80\.2|G81|G82|G83\.[0-49])'),
      STRUCT('charlson', 'renal_disease', 2,
             r'^(I12\.0|I13\.1|N03\.[2-7]|N05\.[2-7]|N18|N19|N25\.0|Z49\.[0-2]|Z94\.0|Z99\.2)'),
      STRUCT('charlson', 'any_malignancy', 2, r'^(C[0-6][0-9]|C7[0-6]|C8[0-8]|C9[0-7])'),
      STRUCT('charlson', 'moderate_severe_liver_disease', 3,
             r'^(I85\.0|I85\.9|I86\.4|I98\.2|K70\.4|K71\.1|K72\.1|K72\.9|K76\.[5-7])'),
      STRUCT('charlson', 'metastatic_solid_tumour', 6, r'^(C77|C78|C79|C80)'),
      STRUCT('charlson', 'aids_hiv', 6, r'^(B2[0-2]|B24)')
    ])
  )
  SELECT
    c.concept_id,
    c.vocabulary_id,
    c.concept_code,
    c.concept_name,
    pat.category_kind,
    pat.category,
    pat.weight
  FROM `{CDR}.concept` AS c
  JOIN pat ON REGEXP_CONTAINS(c.concept_code, pat.pattern)
  WHERE c.vocabulary_id = 'ICD10CM';
  -- @stage-end: cs_condition

  IF (SELECT COUNT(*) FROM `{DERIVED}.cs_condition` WHERE category_kind = 'charlson') = 0
     OR (SELECT COUNT(DISTINCT category) FROM `{DERIVED}.cs_condition` WHERE category_kind = 'charlson') != 17 THEN
    RAISE USING MESSAGE = 'The Quan ICD-10 Charlson mapping did not resolve all seventeen categories against this CDR concept table. Refusing to build a comorbidity score with silently missing categories.';
  END IF;
  END IF;

  -- ===================================================================================
  -- STAGE 4 of 19: episodes
  -- Attrition rung 2, the persons-to-episodes conversion. Qualifying procedure records
  -- on the SAME DATE for the same person collapse into one episode; operations on
  -- different dates stay separate episodes until rung 13 takes the first eligible one.
  --
  -- TWO CLASSIFICATION CHOICES, THE FIRST NOW DECIDED AND PRESPECIFIED
  -- 1. procedure_class uses ALL qualifying evidence in the bundle, add-on codes
  --    included. An add-on arthrodesis code beside a primary laminectomy still
  --    evidences a fusion, and ANALYSIS-PLAN 2.4 classifies decompression plus fusion
  --    on the same date and region as fusion. What add-on codes cannot do is bring an
  --    episode into existence on their own, and that is enforced separately by
  --    n_primary_records at rung 9.
  --    THIS IS NO LONGER AN UNDOCUMENTED CHOICE MADE HERE. The reading implemented
  --    below was put to the human and decided in its favour, and ANALYSIS-PLAN 2.4 is
  --    the section that carries it: fusion status reads ALL qualifying evidence for the
  --    bundle, add-on codes included. 02_pregate.py is matched to the same rule. Any
  --    change is an amendment under plan section 13, not an edit here.
  -- 2. A bundle carrying both cervical and lumbar evidence takes region
  --    'cervical_and_lumbar' rather than either one, so that rung 6 can exclude it as a
  --    simultaneous two-region operation instead of a rule here silently picking a side.
  --
  -- Grain: one row per person per index date. Roughly 12,000 rows against a 9,720
  -- person base cohort.
  -- Every column here is PARTICIPANT-LEVEL. Nothing in this table may be exported.
  -- ===================================================================================
  IF start_ix <= 4 THEN
  -- @stage-begin: episodes
  CREATE OR REPLACE TABLE `{DERIVED}.episodes`
  CLUSTER BY person_id AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  po AS (
    SELECT
      o.person_id,
      o.procedure_date AS index_date,
      o.visit_occurrence_id,
      s.region,
      s.procedure_class,
      s.is_add_on
    FROM `{CDR}.procedure_occurrence` AS o
    JOIN `{DERIVED}.cs_spine` AS s
      ON s.concept_id = o.procedure_source_concept_id
    WHERE o.procedure_date IS NOT NULL
  ),
  agg AS (
    SELECT
      person_id,
      index_date,
      COUNT(*)                                       AS n_procedure_records,
      COUNTIF(NOT is_add_on)                         AS n_primary_records,
      -- Fusion status over the WHOLE bundle, add-on codes included. Prespecified in
      -- ANALYSIS-PLAN 2.4, not chosen here; see the decision note in the stage header.
      LOGICAL_OR(procedure_class = 'fusion')         AS has_fusion,
      LOGICAL_OR(procedure_class = 'decompression')  AS has_decompression,
      LOGICAL_OR(region = 'cervical')                AS has_cervical,
      LOGICAL_OR(region = 'thoracic')                AS has_thoracic,
      LOGICAL_OR(region = 'lumbar')                  AS has_lumbar,
      LOGICAL_OR(region = 'unspecified')             AS has_unspecified,
      ARRAY_AGG(DISTINCT visit_occurrence_id IGNORE NULLS) AS proc_visit_ids
    FROM po
    GROUP BY person_id, index_date
  ),
  -- The index visit is the visit that contains the index date. A visit named on one of
  -- the qualifying procedure records wins; among the rest an inpatient visit wins; ties
  -- break on the earliest start and then on the id, so the choice is deterministic and
  -- a rebuild reproduces it.
  vcand AS (
    SELECT
      a.person_id,
      a.index_date,
      v.visit_occurrence_id,
      v.visit_concept_id,
      v.visit_start_date,
      v.visit_end_date,
      ROW_NUMBER() OVER (
        PARTITION BY a.person_id, a.index_date
        ORDER BY
          IF(v.visit_occurrence_id IN UNNEST(a.proc_visit_ids), 0, 1),
          IF(v.visit_concept_id IN UNNEST(p.inpatient_visit_concept_ids), 0, 1),
          v.visit_start_date,
          v.visit_occurrence_id
      ) AS rn
    FROM agg AS a
    CROSS JOIN p
    JOIN `{CDR}.visit_occurrence` AS v
      ON v.person_id = a.person_id
     AND a.index_date BETWEEN v.visit_start_date
                          AND COALESCE(v.visit_end_date, v.visit_start_date)
  ),
  vpick AS (SELECT * EXCEPT(rn) FROM vcand WHERE rn = 1)
  SELECT
    FORMAT('%d-%s', a.person_id, FORMAT_DATE('%Y%m%d', a.index_date)) AS episode_id,
    a.person_id,
    a.index_date,
    a.n_procedure_records,
    a.n_primary_records,
    a.has_fusion,
    a.has_decompression,
    a.has_cervical,
    a.has_thoracic,
    a.has_lumbar,
    a.has_unspecified,
    IF(a.has_fusion, 'fusion', 'decompression') AS procedure_class,
    CASE
      WHEN a.has_cervical AND a.has_lumbar THEN 'cervical_and_lumbar'
      WHEN a.has_cervical                  THEN 'cervical'
      WHEN a.has_lumbar                    THEN 'lumbar'
      WHEN a.has_thoracic                  THEN 'thoracic'
      ELSE 'unspecified'
    END AS region,
    CASE
      WHEN a.has_cervical AND a.has_lumbar THEN NULL
      WHEN a.has_cervical                  THEN IF(a.has_fusion, 'cervical_fusion', 'cervical_decompression')
      WHEN a.has_lumbar                    THEN IF(a.has_fusion, 'lumbar_fusion', 'lumbar_decompression')
      ELSE NULL
    END AS procedure_group,
    v.visit_occurrence_id                  AS index_visit_occurrence_id,
    v.visit_concept_id                     AS index_visit_concept_id,
    v.visit_start_date,
    v.visit_end_date                       AS discharge_date,
    DATE_DIFF(v.visit_end_date, v.visit_start_date, DAY) AS los_days,
    ROW_NUMBER() OVER (PARTITION BY a.person_id ORDER BY a.index_date) AS episode_seq,
    p.junction_map
  FROM agg AS a
  CROSS JOIN p
  LEFT JOIN vpick AS v
    ON v.person_id = a.person_id AND v.index_date = a.index_date;
  -- @stage-end: episodes
  END IF;

  -- ===================================================================================
  -- STAGE 5 of 19: hr_daily
  -- THE ONLY SCAN OF heart_rate_summary IN THE WHOLE PROJECT, AND THE FIRST OF THE TWO
  -- DYNAMIC STATEMENTS. The second is device_daily at stage 6.
  --
  -- heart_rate_summary is person by date by heart-rate zone with a per-zone minute
  -- count, roughly four rows per person-day against 1,440 for heart_rate_minute_level.
  -- Summing the zone minutes gives the wear figure at about one three-hundredth of the
  -- bytes, and that single fact is what keeps this study under two dollars. The exact
  -- minute column name is a runtime probe, and a column name cannot be a query
  -- parameter, so this one statement is built with FORMAT. The name was shape-checked
  -- against an identifier regex and its existence was confirmed against
  -- INFORMATION_SCHEMA at the top of the procedure, both of which RAISE.
  --
  -- Isolating the scan in its own table means a later rebuild of fitbit_daily under a
  -- different wear rule, or a rebuild of anything downstream, does NOT re-read
  -- heart_rate_summary. This is the single most expensive table in the DAG to lose.
  --
  -- The template contains no literal percent sign other than the two substitutions.
  -- Adding one without doubling it would corrupt the statement, so do not add one.
  -- 03_cohort.py must FORMAT this body BEFORE dry-running it. Dry-running the
  -- unsubstituted template prices a query that is not the one that will execute, so the
  -- estimate is meaningless and this stage's cap is sized against the wrong number.
  -- The @stage-format-args line inside the body below makes that checkable.
  --
  -- Grain: one row per person per date with any heart-rate record. Partitioned by
  -- activity_date, clustered by person_id. PARTICIPANT-LEVEL.
  -- ===================================================================================
  IF start_ix <= 5 THEN
  -- @stage-begin: hr_daily
  -- @stage-format-args: hr_minute_column, hr_minute_column
  -- ^ This body is a FORMAT TEMPLATE. The line above names the FORMAT arguments in
  -- order, one per %s, and 03_cohort.py MUST substitute them before the dry run or the
  -- estimate prices a query that is not the one that will execute. The line sits inside
  -- the @stage-begin / @stage-end pair, so the marker splitter is unchanged and the
  -- requirement travels with the body rather than living only in the file header.
  EXECUTE IMMEDIATE FORMAT("""
    CREATE OR REPLACE TABLE `{DERIVED}.hr_daily`
    PARTITION BY activity_date
    CLUSTER BY person_id AS
    WITH span AS (
      SELECT
        person_id,
        DATE_SUB(MIN(index_date), INTERVAL 60 DAY) AS lo,
        GREATEST(DATE_ADD(MAX(index_date), INTERVAL 120 DAY),
                 DATE_ADD(MAX(IFNULL(discharge_date, index_date)), INTERVAL 90 DAY)) AS hi
      FROM `{DERIVED}.episodes`
      GROUP BY person_id
    )
    SELECT
      h.person_id,
      h.date                                        AS activity_date,
      SAFE_CAST(ROUND(SUM(h.%s)) AS INT64)          AS wear_minutes,
      COUNT(*)                                      AS n_hr_zone_rows,
      SAFE_CAST(ROUND(MAX(h.%s)) AS INT64)          AS max_zone_minutes
    FROM `{CDR}.heart_rate_summary` AS h
    JOIN span AS s
      ON s.person_id = h.person_id
     AND h.date BETWEEN s.lo AND s.hi
    GROUP BY 1, 2
  """, hr_minute_column, hr_minute_column);
  -- @stage-end: hr_daily

  -- THE ZONE-PARTITION CONTINGENCY OF ANALYSIS-PLAN 2.1, ENFORCED RATHER THAN ASSUMED.
  -- The wear figure is only a wear figure if the zones partition the day without
  -- double-counting a minute. A person-date whose summed zone minutes exceed 1,440 is
  -- proof that they do not. The plan's prespecified response is to make sensitivity
  -- definition S2 the primary wear rule and log the substitution as an amendment, which
  -- is a human decision, so the build stops here and names it rather than quietly
  -- carrying an inflated wear minute into every valid-day flag in the study.
  SET zone_overflow_days = (SELECT COUNT(*) FROM `{DERIVED}.hr_daily` WHERE wear_minutes > 1440);
  IF zone_overflow_days > 0 AND primary_wear_definition != 's2' THEN
    RAISE USING MESSAGE = 'Heart-rate zones do not partition the day: at least one person-date sums to more than 1,440 zone minutes. ANALYSIS-PLAN 2.1 prespecifies the response, which is to adopt sensitivity definition S2 as the primary wear rule and record the substitution as an amendment. Re-run with primary_wear_definition = s2 after the amendment is logged. Refusing to build valid-day flags on a wear minute that double-counts.';
  END IF;
  END IF;

  -- ===================================================================================
  -- STAGE 6 of 19: device_daily
  -- Fitbit model records per person, reduced to the fourteen-family vocabulary of
  -- ANALYSIS-PLAN 3.6 by the device_family UDF. The model column is a runtime probe for
  -- the same reason the heart-rate column is, so this is the second and last dynamic
  -- statement. Passing the empty string for device_model_column builds this table empty
  -- with its schema intact, which makes every episode take device family
  -- other_or_unknown downstream. That is a level, not a missing value, and features
  -- records which of the two happened in device_family_source.
  --
  -- Grain: one row per person per device date per family. PARTICIPANT-LEVEL.
  -- ===================================================================================
  IF start_ix <= 6 THEN
  -- @stage-begin: device_daily
  -- @stage-format-args: device_model_column
  -- ^ THE SECOND FORMAT TEMPLATE, and the one that gets missed, because it is on the
  -- ELSE branch below rather than at the top of the body. Same rule as hr_daily: one
  -- name per %s, substituted before the dry run, or the estimate is of the wrong query
  -- and the per-stage cap is sized against the wrong number. When device_model_column
  -- is the empty string the THEN branch runs instead and creates the table empty, which
  -- is the zero-byte case and needs no substitution.
  IF device_model_column = '' THEN
    CREATE OR REPLACE TABLE `{DERIVED}.device_daily` (
      person_id     INT64,
      device_date   DATE,
      device_family STRING,
      n_records     INT64
    );
  ELSE
    EXECUTE IMMEDIATE FORMAT("""
      CREATE OR REPLACE TABLE `{DERIVED}.device_daily`
      CLUSTER BY person_id AS
      WITH span AS (
        SELECT
          person_id,
          DATE_SUB(MIN(index_date), INTERVAL 60 DAY) AS lo,
          GREATEST(DATE_ADD(MAX(index_date), INTERVAL 120 DAY),
                   DATE_ADD(MAX(IFNULL(discharge_date, index_date)), INTERVAL 90 DAY)) AS hi
        FROM `{DERIVED}.episodes`
        GROUP BY person_id
      )
      SELECT
        d.person_id,
        d.device_date,
        `{DERIVED}.device_family`(d.%s) AS device_family,
        COUNT(*)                        AS n_records
      FROM `{CDR}.device` AS d
      JOIN span AS s
        ON s.person_id = d.person_id
       AND d.device_date BETWEEN s.lo AND s.hi
      GROUP BY 1, 2, 3
    """, device_model_column);
  END IF;
  -- @stage-end: device_daily
  END IF;

  -- ===================================================================================
  -- STAGE 7 of 19: fitbit_daily
  -- Person by date over index minus 60 through index plus 120, as a COMPLETE GRID for
  -- every Fitbit-linked participant in the episode set.
  --
  -- THE UPPER BOUND IS EXTENDED TO DISCHARGE PLUS 90 WHERE THE LENGTH OF STAY REQUIRES
  -- IT. Post-discharge day 90 falls on index plus length of stay plus 90, so a stay
  -- longer than 30 days pushes the Arm A horizon past index plus 120. Without the
  -- extension the recovery curve of exactly the sickest episodes would be silently
  -- truncated, and the plan explicitly RETAINS long stays because the estimand is
  -- defined in post-discharge time.
  --
  -- The grid is complete on purpose:
  -- ANALYSIS-PLAN 2.3 requires every day in the window to be exactly one of observed,
  -- missing, censored or inpatient, and a day that is missing because no row exists is
  -- indistinguishable from a day that was never in the window unless the row is there
  -- carrying nulls. has_steps_row and has_hr_row keep "no record" apart from "recorded
  -- zero", which matters because a valid wear day with zero steps contributes a full
  -- day of deficit while a day with no record contributes nothing and is weighted.
  --
  -- The grid is restricted to participants with at least one Fitbit record anywhere.
  -- A participant absent from this table is exactly attrition rung 11, no wearable data,
  -- so the rung is a fact about this table rather than a separate probe.
  --
  -- valid_wear is the EFFECTIVE flag under this run's primary wear definition, which is
  -- the 600-minute rule unless the zone-partition probe of stage 5 forced the
  -- prespecified fallback to S2. Everything downstream reads valid_wear, so the
  -- substitution propagates without a second edit anywhere.
  --
  -- Grain: one row per Fitbit-linked person per date in the window. Roughly 181 rows per
  -- linked participant: on the order of 220,000 rows at the 1,200-participant Fitbit
  -- overlap a sibling project saw, and under 2,000,000 even if every one of the 9,720
  -- base-cohort persons were linked.
  -- PARTITIONED BY activity_date, CLUSTERED BY person_id. See DAG-SCHEMA.md for what
  -- that does and does not buy. PARTICIPANT-LEVEL.
  -- ===================================================================================
  IF start_ix <= 7 THEN
  -- @stage-begin: fitbit_daily
  CREATE OR REPLACE TABLE `{DERIVED}.fitbit_daily`
  PARTITION BY activity_date
  CLUSTER BY person_id AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  span AS (
    SELECT
      person_id,
      DATE_SUB(MIN(index_date), INTERVAL 60 DAY) AS lo,
      GREATEST(DATE_ADD(MAX(index_date), INTERVAL 120 DAY),
               DATE_ADD(MAX(IFNULL(discharge_date, index_date)), INTERVAL 90 DAY)) AS hi
    FROM `{DERIVED}.episodes`
    GROUP BY person_id
  ),
  linked AS (
    SELECT DISTINCT a.person_id
    FROM `{CDR}.activity_summary` AS a
    JOIN span AS s ON s.person_id = a.person_id
    UNION DISTINCT
    SELECT DISTINCT person_id FROM `{DERIVED}.hr_daily`
  ),
  grid AS (
    SELECT s.person_id, day AS activity_date
    FROM span AS s
    JOIN linked AS l ON l.person_id = s.person_id
    CROSS JOIN UNNEST(GENERATE_DATE_ARRAY(s.lo, s.hi)) AS day
  ),
  act AS (
    SELECT a.person_id, a.date AS activity_date, SAFE_CAST(a.steps AS INT64) AS steps
    FROM `{CDR}.activity_summary` AS a
    JOIN span AS s
      ON s.person_id = a.person_id AND a.date BETWEEN s.lo AND s.hi
  )
  SELECT
    g.person_id,
    g.activity_date,
    a.steps,
    h.wear_minutes,
    h.n_hr_zone_rows,
    (a.person_id IS NOT NULL) AS has_steps_row,
    (h.person_id IS NOT NULL) AS has_hr_row,
    `{DERIVED}.is_valid_wear`(h.wear_minutes, a.steps, 'primary') AS valid_wear_primary,
    `{DERIVED}.is_valid_wear`(h.wear_minutes, a.steps, 's1')      AS valid_wear_s1,
    `{DERIVED}.is_valid_wear`(h.wear_minutes, a.steps, 's2')      AS valid_wear_s2,
    `{DERIVED}.is_valid_wear`(h.wear_minutes, a.steps, 's3')      AS valid_wear_s3,
    `{DERIVED}.is_valid_wear`(h.wear_minutes, a.steps, 's4')      AS valid_wear_s4,
    `{DERIVED}.is_valid_wear`(h.wear_minutes, a.steps, p.primary_wear_definition) AS valid_wear,
    -- Analyzable, per 2.1: a valid wear day that also carries a non-null step total.
    -- A valid wear day with a null step total is unobserved and is the target of the
    -- observation weights, not a zero.
    (`{DERIVED}.is_valid_wear`(h.wear_minutes, a.steps, p.primary_wear_definition)
     AND a.steps IS NOT NULL) AS is_analyzable,
    EXTRACT(DAYOFWEEK FROM g.activity_date) AS day_of_week,
    (EXTRACT(DAYOFWEEK FROM g.activity_date) IN (1, 7)) AS is_weekend,
    p.junction_map
  FROM grid AS g
  CROSS JOIN p
  LEFT JOIN act AS a
    ON a.person_id = g.person_id AND a.activity_date = g.activity_date
  LEFT JOIN `{DERIVED}.hr_daily` AS h
    ON h.person_id = g.person_id AND h.activity_date = g.activity_date;
  -- @stage-end: fitbit_daily
  END IF;

  -- ===================================================================================
  -- STAGE 8 of 19: baseline
  -- The preoperative personal baseline B_i of ANALYSIS-PLAN 2.2: the MEDIAN valid daily
  -- step count over index day minus 30 through minus 8. The final seven preoperative
  -- days are excluded because pain flares, preoperative testing, travel and
  -- preoperative instructions alter activity. The median rather than the mean limits
  -- the influence of isolated high-activity days, and it is the exact-median UDF for
  -- the reason set out at the top of this file.
  --
  -- Eight alternative baselines are computed here rather than downstream, because each
  -- one is a different median over the SAME scan and recomputing them later would mean
  -- re-reading fitbit_daily once per sensitivity row. Two vary the window (section 6
  -- row 7) and four vary the wear rule (section 6 row 6), and changing the wear rule
  -- changes which days are valid and therefore changes B_i itself, which is the reason
  -- a wear sensitivity cannot be run by swapping a flag at model time.
  --
  -- THE LAST TWO SPLIT THE WEEK, AND THE PROTOCOL IS WHAT ASKS FOR THEM. The protocol's
  -- baseline section says the day-of-week composition will be recorded AND that a
  -- sensitivity analysis will estimate weekday and weekend baselines separately. The
  -- composition alone cannot run that sensitivity: it says how many Sundays are in the
  -- window, not what the participant walked on them. Weekend is Saturday and Sunday, the
  -- same split ANALYSIS-PLAN 5.5 uses for the Arm A landmark relaxation, and day_of_week
  -- is 1 for Sunday through 7 for Saturday, so weekday is 2 through 6.
  --
  -- EACH SPLIT MEDIAN CARRIES ITS OWN VALID-DAY COUNT, AND THAT COUNT IS THE
  -- DENOMINATOR. Not every episode has a valid day in both halves of the week: a
  -- participant who charges the device at weekends can have an adequate baseline overall
  -- and no weekend baseline at all. A sensitivity fitted on one of these two is fitted
  -- on the episodes where that one exists, which is a DIFFERENT set from the primary's,
  -- and Table 2 prints that set's own n rather than the primary's.
  --
  -- A null baseline_steps means no valid day in the window. It is never zero: a zero
  -- baseline would make normalized activity infinite and the daily deficit silently
  -- equal to one on every day, manufacturing a maximal recovery debt out of an absence
  -- of data. Attrition rung 12 removes those episodes and counts them.
  --
  -- Grain: one row per episode, INCLUDING episodes with no wearable data, so that the
  -- ladder can count them. Roughly 12,000 rows. PARTICIPANT-LEVEL.
  -- ===================================================================================
  IF start_ix <= 8 THEN
  -- @stage-begin: baseline
  CREATE OR REPLACE TABLE `{DERIVED}.baseline`
  CLUSTER BY person_id AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  linked AS (SELECT DISTINCT person_id FROM `{DERIVED}.fitbit_daily`),
  d AS (
    SELECT
      e.episode_id,
      e.person_id,
      e.index_date,
      f.activity_date,
      f.steps,
      f.day_of_week,
      f.valid_wear,
      f.valid_wear_s1,
      f.valid_wear_s2,
      f.valid_wear_s3,
      f.valid_wear_s4,
      DATE_DIFF(f.activity_date, e.index_date, DAY) AS rel_day
    FROM `{DERIVED}.episodes` AS e
    LEFT JOIN `{DERIVED}.fitbit_daily` AS f
      ON f.person_id = e.person_id
     AND f.activity_date BETWEEN DATE_SUB(e.index_date, INTERVAL 60 DAY)
                             AND DATE_SUB(e.index_date, INTERVAL 1 DAY)
  ),
  agg AS (
    SELECT
      episode_id,
      ANY_VALUE(person_id)  AS person_id,
      ANY_VALUE(index_date) AS index_date,

      -- The locked baseline: days -30 to -8, effective wear rule, non-null steps.
      `{DERIVED}.exact_median`(ARRAY_AGG(
         IF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL,
            CAST(steps AS FLOAT64), NULL) IGNORE NULLS)) AS baseline_steps,
      COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL)
                                                          AS n_valid_baseline_days,
      DATE_DIFF(
        MAX(IF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL, activity_date, NULL)),
        MIN(IF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL, activity_date, NULL)),
        DAY) + 1                                          AS baseline_span_days,

      -- Day-of-week composition of the baseline window, recorded per episode and
      -- reported in aggregate (2.2). Index 1 is Sunday, index 7 is Saturday.
      [COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL AND day_of_week = 1),
       COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL AND day_of_week = 2),
       COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL AND day_of_week = 3),
       COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL AND day_of_week = 4),
       COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL AND day_of_week = 5),
       COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL AND day_of_week = 6),
       COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL AND day_of_week = 7)]
                                                          AS baseline_dow_counts,

      -- The protocol's weekday and weekend baselines, on the locked minus 30 to minus 8
      -- window and under the effective wear rule, so that only the half of the week
      -- varies. exact_median_int, never an approximate two-quantile expression: a
      -- weekday half of a sparse window can carry as few as two valid days, which is the
      -- even-length case the approximate form gets wrong in one direction.
      -- A median over NO valid day is NULL and never 0, by the same rule as
      -- baseline_steps itself. A zero baseline makes S/B infinite and the deficit
      -- silently 1 on every day, which manufactures a maximal recovery debt out of
      -- missing data, and it would do so here on exactly the participants whose wear is
      -- concentrated in the other half of the week.
      `{DERIVED}.exact_median_int`(ARRAY_AGG(
         IF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL
            AND day_of_week BETWEEN 2 AND 6, steps, NULL) IGNORE NULLS))
                                                          AS baseline_steps_weekday,
      COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL
              AND day_of_week BETWEEN 2 AND 6)            AS n_valid_baseline_days_weekday,
      `{DERIVED}.exact_median_int`(ARRAY_AGG(
         IF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL
            AND day_of_week IN (1, 7), steps, NULL) IGNORE NULLS))
                                                          AS baseline_steps_weekend,
      COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear AND steps IS NOT NULL
              AND day_of_week IN (1, 7))                  AS n_valid_baseline_days_weekend,

      -- Sensitivity ladder row 7: alternative baseline windows.
      `{DERIVED}.exact_median`(ARRAY_AGG(
         IF(rel_day BETWEEN -60 AND -15 AND valid_wear AND steps IS NOT NULL,
            CAST(steps AS FLOAT64), NULL) IGNORE NULLS)) AS baseline_steps_60_15,
      COUNTIF(rel_day BETWEEN -60 AND -15 AND valid_wear AND steps IS NOT NULL)
                                                          AS n_valid_baseline_days_60_15,
      `{DERIVED}.exact_median`(ARRAY_AGG(
         IF(rel_day BETWEEN -30 AND -1 AND valid_wear AND steps IS NOT NULL,
            CAST(steps AS FLOAT64), NULL) IGNORE NULLS)) AS baseline_steps_30_1,
      COUNTIF(rel_day BETWEEN -30 AND -1 AND valid_wear AND steps IS NOT NULL)
                                                          AS n_valid_baseline_days_30_1,

      -- Sensitivity ladder row 6: the four alternative wear definitions, each on the
      -- locked minus 30 to minus 8 window.
      `{DERIVED}.exact_median`(ARRAY_AGG(
         IF(rel_day BETWEEN -30 AND -8 AND valid_wear_s1 AND steps IS NOT NULL,
            CAST(steps AS FLOAT64), NULL) IGNORE NULLS)) AS baseline_steps_s1,
      COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear_s1 AND steps IS NOT NULL)
                                                          AS n_valid_baseline_days_s1,
      `{DERIVED}.exact_median`(ARRAY_AGG(
         IF(rel_day BETWEEN -30 AND -8 AND valid_wear_s2 AND steps IS NOT NULL,
            CAST(steps AS FLOAT64), NULL) IGNORE NULLS)) AS baseline_steps_s2,
      COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear_s2 AND steps IS NOT NULL)
                                                          AS n_valid_baseline_days_s2,
      `{DERIVED}.exact_median`(ARRAY_AGG(
         IF(rel_day BETWEEN -30 AND -8 AND valid_wear_s3 AND steps IS NOT NULL,
            CAST(steps AS FLOAT64), NULL) IGNORE NULLS)) AS baseline_steps_s3,
      COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear_s3 AND steps IS NOT NULL)
                                                          AS n_valid_baseline_days_s3,
      `{DERIVED}.exact_median`(ARRAY_AGG(
         IF(rel_day BETWEEN -30 AND -8 AND valid_wear_s4 AND steps IS NOT NULL,
            CAST(steps AS FLOAT64), NULL) IGNORE NULLS)) AS baseline_steps_s4,
      COUNTIF(rel_day BETWEEN -30 AND -8 AND valid_wear_s4 AND steps IS NOT NULL)
                                                          AS n_valid_baseline_days_s4
    FROM d
    GROUP BY episode_id
  )
  SELECT
    agg.* EXCEPT(baseline_span_days),
    IFNULL(agg.baseline_span_days, 0) AS baseline_span_days,
    -- Fixed description bands (3.6). Used for description only and never as a model
    -- cutpoint, which is why they are slugs here and a label lookup at render time.
    CASE
      WHEN agg.baseline_steps IS NULL   THEN NULL
      WHEN agg.baseline_steps < 3000    THEN 'under_3000'
      WHEN agg.baseline_steps < 7000    THEN '3000_to_6999'
      ELSE '7000_or_more'
    END AS baseline_band_slug,
    -- Sensitivity ladder row 9. A FLAG, never a filter applied here: the baseline floor
    -- is a sensitivity and not an eligibility criterion (3.10).
    (agg.baseline_steps >= 1000) AS meets_baseline_floor,
    (l.person_id IS NOT NULL)    AS has_any_fitbit,
    p.junction_map
  FROM agg
  CROSS JOIN p
  LEFT JOIN linked AS l ON l.person_id = agg.person_id;
  -- @stage-end: baseline
  END IF;

  -- ===================================================================================
  -- STAGE 9 of 19: episodes_eligible
  -- THE EXCLUSIONS TABLE. It is NOT the filtered survivor set: it carries ONE ROW PER
  -- EPISODE from the episodes table, every exclusion flag, and the FIRST rung the
  -- episode fails. Filter on is_eligible to get survivors.
  --
  -- It is built this way because the ladder of ANALYSIS-PLAN 2.6 counts an episode ONCE,
  -- at the first rung it fails, and that is what makes the ladder close. A cascade of
  -- filtered tables would make the attribution implicit and would make the per-reason
  -- breakdown, where an episode may be counted under more than one reason, impossible
  -- to produce afterwards. Both come out of this one table: first_fail_step drives the
  -- ladder and the individual flags drive ledger_exclusion_reasons.
  --
  -- The rung order is fixed by the plan and is not an implementation detail. Reordering
  -- changes every rung's n_dropped without changing the analytic n, which changes what
  -- the Figure 1 exclusion boxes say. Reordering is an amendment under section 13.
  --
  -- Grain: one row per episode. Roughly 12,000 rows. PARTICIPANT-LEVEL.
  -- ===================================================================================
  IF start_ix <= 9 THEN
  -- @stage-begin: episodes_eligible
  CREATE OR REPLACE TABLE `{DERIVED}.episodes_eligible`
  CLUSTER BY person_id AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  e AS (
    SELECT
      ep.*,
      b.baseline_steps,
      b.n_valid_baseline_days,
      b.baseline_span_days,
      b.has_any_fitbit
    FROM `{DERIVED}.episodes` AS ep
    JOIN `{DERIVED}.baseline` AS b USING (episode_id)
  ),
  persons AS (SELECT DISTINCT person_id FROM `{DERIVED}.episodes`),

  -- Rung 4, the elective proxy. "Immediately preceding" is fixed at an emergency
  -- department visit whose END date falls on the index date or on either of the two
  -- calendar days before it. Two days rather than one, because an emergency
  -- presentation late on a Friday that leads to a Monday operation is exactly the case
  -- the criterion is about and a same-day rule would miss it.
  ed AS (
    SELECT
      e.episode_id,
      TRUE                                        AS ed_encounter_present,
      ARRAY_AGG(DISTINCT v.visit_occurrence_id)   AS ed_visit_ids
    FROM e
    CROSS JOIN p
    JOIN `{CDR}.visit_occurrence` AS v
      ON v.person_id = e.person_id
     AND v.visit_concept_id IN UNNEST(p.ed_visit_concept_ids)
     AND COALESCE(v.visit_end_date, v.visit_start_date)
           BETWEEN DATE_SUB(e.index_date, INTERVAL 2 DAY) AND e.index_date
    GROUP BY e.episode_id
  ),

  cond AS (
    SELECT
      c.person_id,
      c.condition_start_date,
      c.visit_occurrence_id,
      s.category_kind,
      s.category
    FROM `{CDR}.condition_occurrence` AS c
    JOIN persons AS pr ON pr.person_id = c.person_id
    JOIN `{DERIVED}.cs_condition` AS s
      ON s.concept_id = c.condition_source_concept_id
    WHERE s.category_kind IN ('nonelective_indication', 'degenerative_spine')
  ),

  -- Rung 3 is a COMPOSITE screen over one 30-day lookback, applied as one rung. The
  -- five indication flags beside it exist for the exclusion-reason ledger, where rows
  -- may overlap and are explicitly not a partition.
  condagg AS (
    SELECT
      e.episode_id,
      LOGICAL_OR(c.category = 'trauma'             AND c.condition_start_date BETWEEN DATE_SUB(e.index_date, INTERVAL 30 DAY) AND e.index_date) AS ind_trauma,
      LOGICAL_OR(c.category = 'spinal_cord_injury' AND c.condition_start_date BETWEEN DATE_SUB(e.index_date, INTERVAL 30 DAY) AND e.index_date) AS ind_spinal_cord_injury,
      LOGICAL_OR(c.category = 'malignancy'         AND c.condition_start_date BETWEEN DATE_SUB(e.index_date, INTERVAL 30 DAY) AND e.index_date) AS ind_malignancy,
      LOGICAL_OR(c.category = 'metastatic_disease' AND c.condition_start_date BETWEEN DATE_SUB(e.index_date, INTERVAL 30 DAY) AND e.index_date) AS ind_metastatic_disease,
      LOGICAL_OR(c.category = 'spinal_infection'   AND c.condition_start_date BETWEEN DATE_SUB(e.index_date, INTERVAL 30 DAY) AND e.index_date) AS ind_spinal_infection,
      -- Rescue route 2, first half: a degenerative index diagnosis on the index encounter.
      LOGICAL_OR(c.category_kind = 'degenerative_spine'
                 AND c.visit_occurrence_id = e.index_visit_occurrence_id)            AS deg_on_index_encounter,
      -- Rescue route 2, second half: nothing from the step 3 sets on the ED encounter.
      LOGICAL_OR(c.category_kind = 'nonelective_indication'
                 AND c.visit_occurrence_id IN UNNEST(IFNULL(ed.ed_visit_ids, ARRAY<INT64>[])))   AS indication_on_ed_encounter,
      -- Rescue route 3: a degenerative spine diagnosis on a visit that is neither an
      -- emergency department visit nor an inpatient admission, in the 90 days before
      -- the index date. The outpatient setting is defined by exclusion from the two
      -- enumerated visit sets, because no outpatient concept id was probed.
      LOGICAL_OR(c.category_kind = 'degenerative_spine'
                 AND c.condition_start_date BETWEEN DATE_SUB(e.index_date, INTERVAL 90 DAY)
                                                AND DATE_SUB(e.index_date, INTERVAL 1 DAY)
                 AND NOT COALESCE(vo.visit_concept_id IN UNNEST(p.ed_visit_concept_ids), FALSE)
                 AND NOT COALESCE(vo.visit_concept_id IN UNNEST(p.inpatient_visit_concept_ids), FALSE))
                                                                                     AS deg_outpatient_90d
    FROM e
    CROSS JOIN p
    LEFT JOIN ed USING (episode_id)
    LEFT JOIN cond AS c
      ON c.person_id = e.person_id
     AND c.condition_start_date BETWEEN DATE_SUB(e.index_date, INTERVAL 90 DAY) AND e.index_date
    LEFT JOIN `{CDR}.visit_occurrence` AS vo
      ON vo.visit_occurrence_id = c.visit_occurrence_id
    GROUP BY e.episode_id
  ),

  -- Rescue route 1. A PROXY, and labelled as one in the Methods: it reads the visit
  -- source value for elective or scheduled wording. visit_detail is deliberately not
  -- consulted, because whether the CDR populates it is an unconfirmed runtime probe and
  -- a rescue that silently never fires is worse than one that is narrow and named.
  elect AS (
    SELECT
      e.episode_id,
      COALESCE(REGEXP_CONTAINS(LOWER(IFNULL(v.visit_source_value, '')), r'elect|sched'), FALSE)
        AS rescue_elective_coded
    FROM e
    LEFT JOIN `{CDR}.visit_occurrence` AS v
      ON v.visit_occurrence_id = e.index_visit_occurrence_id
  ),

  -- Rung 5. A prior qualifying spine operation in the 90 days before the index date.
  prior AS (
    SELECT
      e.episode_id,
      LOGICAL_OR(o.index_date BETWEEN DATE_SUB(e.index_date, INTERVAL 90 DAY)
                                  AND DATE_SUB(e.index_date, INTERVAL 1 DAY)) AS prior_operation_90_days
    FROM e
    LEFT JOIN `{DERIVED}.episodes` AS o
      ON o.person_id = e.person_id AND o.index_date < e.index_date
    GROUP BY e.episode_id
  ),

  -- Censoring (2.3). Not "missing": a censored day is a day the episode is not at risk
  -- on, and it shortens the window rather than being weighted.
  obs AS (
    SELECT person_id, MAX(observation_period_end_date) AS obs_end
    FROM `{CDR}.observation_period`
    JOIN persons USING (person_id)
    GROUP BY person_id
  ),
  cens AS (
    SELECT
      e.episode_id,
      dt.death_date,
      (SELECT MIN(o.index_date)
       FROM `{DERIVED}.episodes` AS o
       WHERE o.person_id = e.person_id AND o.index_date > e.discharge_date) AS repeat_operation_date,
      COALESCE(obs.obs_end, p.cdr_observation_cutoff) AS observation_end_date
    FROM e
    CROSS JOIN p
    LEFT JOIN obs ON obs.person_id = e.person_id
    LEFT JOIN `{CDR}.death` AS dt ON dt.person_id = e.person_id
  ),
  cens2 AS (
    SELECT
      episode_id,
      death_date,
      repeat_operation_date,
      observation_end_date,
      (SELECT MIN(x) FROM UNNEST([death_date, repeat_operation_date, observation_end_date]) AS x)
        AS censor_date
    FROM cens
  ),

  -- Rungs 14 and 15 need the post-discharge day 1 to 35 window. An episode clears rung
  -- 14 when it is at risk on at least one day of that window AND contributes at least
  -- one ANALYZABLE day inside it. The second condition is the binding one: an episode
  -- with zero analyzable days contributes nothing to the fit, and integrating a 35-day
  -- debt for it would be extrapolation with no observation of its own to anchor it.
  wear AS (
    SELECT
      e.episode_id,
      COUNTIF(f.is_analyzable) AS n_analyzable_days_1_35,
      COUNT(f.activity_date)   AS n_at_risk_days_1_35
    FROM e
    LEFT JOIN cens2 AS c USING (episode_id)
    LEFT JOIN `{DERIVED}.fitbit_daily` AS f
      ON f.person_id = e.person_id
     AND f.activity_date BETWEEN DATE_ADD(e.discharge_date, INTERVAL 1 DAY)
                             AND DATE_ADD(e.discharge_date, INTERVAL 35 DAY)
     AND (c.censor_date IS NULL OR f.activity_date <= c.censor_date)
    GROUP BY e.episode_id
  ),
  flags AS (
    SELECT
      e.episode_id,
      e.person_id,
      e.index_date,
      e.discharge_date,
      c.death_date,
      c.repeat_operation_date,
      c.observation_end_date,
      c.censor_date,
      CASE
        WHEN c.censor_date IS NULL                                                        THEN 'none'
        WHEN c.death_date IS NOT NULL            AND c.censor_date = c.death_date         THEN 'death'
        WHEN c.repeat_operation_date IS NOT NULL AND c.censor_date = c.repeat_operation_date THEN 'repeat_spine_operation'
        ELSE 'cdr_observation_cutoff'
      END AS censor_reason,
      IFNULL(w.n_analyzable_days_1_35, 0) AS n_analyzable_days_1_35,
      IFNULL(w.n_at_risk_days_1_35, 0)    AS n_at_risk_days_1_35,

      IFNULL(ca.ind_trauma, FALSE)                 AS ind_trauma,
      IFNULL(ca.ind_spinal_cord_injury, FALSE)     AS ind_spinal_cord_injury,
      IFNULL(ca.ind_malignancy, FALSE)             AS ind_malignancy,
      IFNULL(ca.ind_metastatic_disease, FALSE)     AS ind_metastatic_disease,
      IFNULL(ca.ind_spinal_infection, FALSE)       AS ind_spinal_infection,
      IFNULL(ed.ed_encounter_present, FALSE)       AS ed_encounter_present,
      IFNULL(el.rescue_elective_coded, FALSE)      AS rescue_elective_coded,
      (IFNULL(ca.deg_on_index_encounter, FALSE)
        AND NOT IFNULL(ca.indication_on_ed_encounter, FALSE)) AS rescue_degenerative_index,
      IFNULL(ca.deg_outpatient_90d, FALSE)         AS rescue_degenerative_outpatient_90d,

      -- The thirteen exclusion predicates, in rung order. Each is a property of the
      -- episode and is evaluated for EVERY episode; which one gets the count is decided
      -- by first_fail_step below, never by a filter.
      (IFNULL(ca.ind_trauma, FALSE) OR IFNULL(ca.ind_spinal_cord_injury, FALSE)
        OR IFNULL(ca.ind_malignancy, FALSE) OR IFNULL(ca.ind_metastatic_disease, FALSE)
        OR IFNULL(ca.ind_spinal_infection, FALSE))                    AS x_trauma_malignancy_infection,
      (IFNULL(ed.ed_encounter_present, FALSE)
        AND NOT (IFNULL(el.rescue_elective_coded, FALSE)
                 OR (IFNULL(ca.deg_on_index_encounter, FALSE)
                     AND NOT IFNULL(ca.indication_on_ed_encounter, FALSE))
                 OR IFNULL(ca.deg_outpatient_90d, FALSE)))            AS x_ed_encounter_not_elective,
      IFNULL(pr.prior_operation_90_days, FALSE)                       AS x_prior_operation_90_days,
      (e.region = 'cervical_and_lumbar')                              AS x_simultaneous_cervical_lumbar,
      (e.region = 'unspecified')                                      AS x_region_unspecified_only,
      (e.region = 'thoracic')                                         AS x_thoracic_only,
      (e.n_primary_records = 0)                                       AS x_add_on_code_only,
      (e.discharge_date IS NULL)                                      AS x_missing_discharge_date,
      (NOT e.has_any_fitbit)                                          AS x_no_wearable_data,
      (e.baseline_steps IS NULL OR e.n_valid_baseline_days < 7 OR e.baseline_span_days < 14)
                                                                      AS x_inadequate_baseline_wear,
      (IFNULL(w.n_analyzable_days_1_35, 0) = 0 OR IFNULL(w.n_at_risk_days_1_35, 0) = 0)
                                                                      AS x_no_computable_post_discharge_window,
      (CASE
         WHEN c.censor_date IS NULL THEN FALSE
         WHEN c.death_date IS NOT NULL AND c.censor_date = c.death_date
              AND c.censor_date <= DATE_ADD(e.discharge_date, INTERVAL 35 DAY) THEN TRUE
         WHEN c.repeat_operation_date IS NOT NULL AND c.censor_date = c.repeat_operation_date
              AND c.censor_date <= DATE_ADD(e.discharge_date, INTERVAL 35 DAY) THEN TRUE
         ELSE FALSE
       END)                                                           AS x_window_truncated_by_death_or_reoperation
    FROM e
    LEFT JOIN ed      USING (episode_id)
    LEFT JOIN condagg AS ca USING (episode_id)
    LEFT JOIN elect   AS el USING (episode_id)
    LEFT JOIN prior   AS pr USING (episode_id)
    LEFT JOIN cens2   AS c  USING (episode_id)
    LEFT JOIN wear    AS w  USING (episode_id)
  ),

  -- Rung 13, the first eligible episode. It is a rung and not prose because it is a
  -- real reduction between rung 12 and the analytic cohort, and an uncounted reduction
  -- breaks the closure assert on the first real run. Person and episode therefore
  -- coincide in the primary, which is what makes the person random effects and the
  -- person-clustered bootstrap coherent: the resampling unit and the outcome unit are
  -- the same object. A tie inside a participant cannot occur, because same-date records
  -- were collapsed at rung 2.
  seq AS (
    SELECT
      f.*,
      (NOT (f.x_trauma_malignancy_infection OR f.x_ed_encounter_not_elective
            OR f.x_prior_operation_90_days OR f.x_simultaneous_cervical_lumbar
            OR f.x_region_unspecified_only OR f.x_thoracic_only OR f.x_add_on_code_only
            OR f.x_missing_discharge_date OR f.x_no_wearable_data
            OR f.x_inadequate_baseline_wear)) AS passes_through_12
    FROM flags AS f
  ),
  ranked AS (
    SELECT
      s.*,
      SUM(CAST(s.passes_through_12 AS INT64)) OVER (
        PARTITION BY s.person_id ORDER BY s.index_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS eligible_rank
    FROM seq AS s
  )
  SELECT
    r.* EXCEPT(passes_through_12, eligible_rank),
    (r.passes_through_12 AND r.eligible_rank > 1) AS x_not_first_eligible_episode,
    CASE
      WHEN r.x_trauma_malignancy_infection                THEN 3
      WHEN r.x_ed_encounter_not_elective                  THEN 4
      WHEN r.x_prior_operation_90_days                    THEN 5
      WHEN r.x_simultaneous_cervical_lumbar               THEN 6
      WHEN r.x_region_unspecified_only                    THEN 7
      WHEN r.x_thoracic_only                              THEN 8
      WHEN r.x_add_on_code_only                           THEN 9
      WHEN r.x_missing_discharge_date                     THEN 10
      WHEN r.x_no_wearable_data                           THEN 11
      WHEN r.x_inadequate_baseline_wear                   THEN 12
      WHEN r.passes_through_12 AND r.eligible_rank > 1    THEN 13
      WHEN r.x_no_computable_post_discharge_window        THEN 14
      WHEN r.x_window_truncated_by_death_or_reoperation   THEN 15
      ELSE NULL
    END AS first_fail_step,
    CASE
      WHEN r.x_trauma_malignancy_infection                THEN 'excl_trauma_malignancy_infection'
      WHEN r.x_ed_encounter_not_elective                  THEN 'excl_ed_encounter_not_elective'
      WHEN r.x_prior_operation_90_days                    THEN 'excl_prior_operation_90_days'
      WHEN r.x_simultaneous_cervical_lumbar               THEN 'excl_simultaneous_cervical_lumbar'
      WHEN r.x_region_unspecified_only                    THEN 'excl_region_unspecified_only'
      WHEN r.x_thoracic_only                              THEN 'excl_thoracic_only'
      WHEN r.x_add_on_code_only                           THEN 'excl_add_on_code_only'
      WHEN r.x_missing_discharge_date                     THEN 'excl_missing_discharge_date'
      WHEN r.x_no_wearable_data                           THEN 'excl_no_wearable_data'
      WHEN r.x_inadequate_baseline_wear                   THEN 'excl_inadequate_baseline_wear'
      WHEN r.passes_through_12 AND r.eligible_rank > 1    THEN 'excl_not_first_eligible_episode'
      WHEN r.x_no_computable_post_discharge_window        THEN 'excl_no_computable_post_discharge_window'
      WHEN r.x_window_truncated_by_death_or_reoperation   THEN 'excl_window_truncated_by_death_or_reoperation'
      ELSE NULL
    END AS first_fail_slug,
    (r.x_trauma_malignancy_infection OR r.x_ed_encounter_not_elective
     OR r.x_prior_operation_90_days OR r.x_simultaneous_cervical_lumbar
     OR r.x_region_unspecified_only OR r.x_thoracic_only OR r.x_add_on_code_only
     OR r.x_missing_discharge_date OR r.x_no_wearable_data OR r.x_inadequate_baseline_wear
     OR (r.passes_through_12 AND r.eligible_rank > 1)
     OR r.x_no_computable_post_discharge_window
     OR r.x_window_truncated_by_death_or_reoperation) = FALSE AS is_eligible,
    p.junction_map
  FROM ranked AS r
  CROSS JOIN p;
  -- @stage-end: episodes_eligible
  END IF;

  -- ===================================================================================
  -- STAGE 10 of 19: features
  -- The analysis-ready covariate frame, one row per ANALYTIC episode. Everything the
  -- locked covariate table of ANALYSIS-PLAN 3.6 names, plus the quantities Table 1
  -- reports, plus ALL EIGHT alternative baselines the sensitivity ladder needs, carried
  -- forward so that no sensitivity row has to re-read fitbit_daily and none has to reach
  -- back to the baseline table for a column this one was supposed to carry.
  --
  -- Grain: one row per eligible episode, which is one row per participant, because rung
  -- 13 takes the first eligible episode per person. Order of 300 to 600 rows.
  -- PARTICIPANT-LEVEL.
  -- ===================================================================================
  IF start_ix <= 10 THEN
  -- Sex assigned at birth is an All of Us extension to the OMOP person table rather
  -- than a CDM guarantee. Fail loudly here rather than let a covariate the primary
  -- model adjusts for resolve to a column that is not there.
  IF (SELECT COUNT(*)
      FROM `{CDR}.INFORMATION_SCHEMA.COLUMNS`
      WHERE table_name = 'person' AND column_name = 'sex_at_birth_concept_id') = 0 THEN
    RAISE USING MESSAGE = 'The person table does not carry sex_at_birth_concept_id. ANALYSIS-PLAN 3.6 adjusts for sex assigned at birth, not gender identity, so this is a stop condition rather than a substitution to be made silently.';
  END IF;

  -- @stage-begin: features
  CREATE OR REPLACE TABLE `{DERIVED}.features`
  CLUSTER BY person_id AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  elig AS (
    SELECT
      x.episode_id, x.person_id, x.index_date,
      x.censor_date, x.censor_reason,
      x.n_analyzable_days_1_35, x.n_at_risk_days_1_35,
      e.discharge_date, e.los_days, e.region, e.procedure_class, e.procedure_group,
      e.index_visit_occurrence_id
    FROM `{DERIVED}.episodes_eligible` AS x
    JOIN `{DERIVED}.episodes` AS e USING (episode_id)
    WHERE x.is_eligible
  ),

  -- Charlson, Quan ICD-10 mapping over the 365 days before index. The three hierarchy
  -- rules are applied here and not in the vocabulary table, because they are a scoring
  -- rule rather than a vocabulary fact: metastatic solid tumour supersedes any
  -- malignancy, moderate or severe liver disease supersedes mild, and diabetes with
  -- complication supersedes diabetes without.
  cc AS (
    SELECT e.episode_id, s.category, ANY_VALUE(s.weight) AS weight
    FROM elig AS e
    JOIN `{CDR}.condition_occurrence` AS c
      ON c.person_id = e.person_id
     AND c.condition_start_date BETWEEN DATE_SUB(e.index_date, INTERVAL 365 DAY) AND e.index_date
    JOIN `{DERIVED}.cs_condition` AS s
      ON s.concept_id = c.condition_source_concept_id AND s.category_kind = 'charlson'
    GROUP BY e.episode_id, s.category
  ),
  charlson AS (
    SELECT
      episode_id,
      IFNULL(SUM(IF(category IN ('any_malignancy','metastatic_solid_tumour',
                                 'mild_liver_disease','moderate_severe_liver_disease',
                                 'diabetes_without_complication','diabetes_with_complication'),
                    0, weight)), 0)
      + IF(LOGICAL_OR(category = 'metastatic_solid_tumour'), 6,
           IF(LOGICAL_OR(category = 'any_malignancy'), 2, 0))
      + IF(LOGICAL_OR(category = 'moderate_severe_liver_disease'), 3,
           IF(LOGICAL_OR(category = 'mild_liver_disease'), 1, 0))
      + IF(LOGICAL_OR(category = 'diabetes_with_complication'), 2,
           IF(LOGICAL_OR(category = 'diabetes_without_complication'), 1, 0)) AS charlson_score
    FROM cc
    GROUP BY episode_id
  ),

  -- Body mass index: the NEAREST measurement in the 365 days before index. The
  -- plausibility window of 10 to 80 kg/m2 is a stated choice made here, and it exists
  -- so that a transcription error does not become a spline knot's neighbourhood.
  bmi_raw AS (
    SELECT episode_id, bmi FROM (
      SELECT
        e.episode_id,
        m.value_as_number AS bmi,
        ROW_NUMBER() OVER (PARTITION BY e.episode_id
                           ORDER BY m.measurement_date DESC, m.measurement_id) AS rn
      FROM elig AS e
      JOIN `{CDR}.measurement` AS m
        ON m.person_id = e.person_id
       AND m.measurement_concept_id = 3038553
       AND m.measurement_date BETWEEN DATE_SUB(e.index_date, INTERVAL 365 DAY) AND e.index_date
       AND m.value_as_number BETWEEN 10 AND 80
    )
    WHERE rn = 1
  ),
  -- Median substitution, computed inside the perimeter and never printed. The exact
  -- median again: an even-length cohort would otherwise take the upper of the two
  -- middle values and shift every imputed episode upward.
  bmi_med AS (
    SELECT `{DERIVED}.exact_median`(ARRAY_AGG(bmi IGNORE NULLS)) AS bmi_median FROM bmi_raw
  ),

  -- The device family at baseline is the modal family in the 30 days before index, ties
  -- broken by the most recent record and then by the family name, so the choice is
  -- deterministic. Written as a window rather than a correlated subquery with a LIMIT,
  -- because a correlated LIMIT is the kind of construct an engine is free to refuse.
  dev_base AS (
    SELECT episode_id, device_family AS device_family_baseline
    FROM (
      SELECT
        e.episode_id,
        d.device_family,
        ROW_NUMBER() OVER (PARTITION BY e.episode_id
                           ORDER BY d.n_records DESC, d.device_date DESC, d.device_family) AS rn
      FROM elig AS e
      JOIN `{DERIVED}.device_daily` AS d
        ON d.person_id = e.person_id
       AND d.device_date BETWEEN DATE_SUB(e.index_date, INTERVAL 30 DAY) AND e.index_date
    )
    WHERE rn = 1
  ),
  -- Sensitivity ladder row 8: a device change between baseline and post-discharge day 90
  -- can shift step counts by more than the effect being measured.
  dev_change AS (
    SELECT e.episode_id, COUNT(DISTINCT d.device_family) AS n_device_families
    FROM elig AS e
    LEFT JOIN `{DERIVED}.device_daily` AS d
      ON d.person_id = e.person_id
     AND d.device_date BETWEEN DATE_SUB(e.index_date, INTERVAL 30 DAY)
                           AND DATE_ADD(e.discharge_date, INTERVAL 90 DAY)
    GROUP BY e.episode_id
  )
  SELECT
    e.episode_id,
    e.person_id,
    e.index_date,
    e.discharge_date,
    e.los_days,
    e.region,
    e.procedure_class,
    e.procedure_group,
    (e.procedure_class = 'fusion') AS fusion,
    DATE_DIFF(e.index_date, DATE(pe.birth_datetime), DAY) / 365.25 AS age_at_index,
    CASE pe.sex_at_birth_concept_id
      WHEN 45880669 THEN 'female'
      WHEN 45878463 THEN 'male'
      WHEN 8532      THEN 'female'
      WHEN 8507      THEN 'male'
      ELSE 'other_or_unknown'
    END AS sex_at_birth,
    pe.race_concept_id,
    pe.ethnicity_concept_id,
    b.bmi,
    (b.bmi IS NULL) AS bmi_missing,
    COALESCE(b.bmi, (SELECT bmi_median FROM bmi_med)) AS bmi_imputed,
    IFNULL(ch.charlson_score, 0) AS charlson_score,
    -- The IFNULL above is a SCORING rule, not an imputation: an episode with no qualifying
    -- condition in the lookback genuinely scores zero. But it also destroys the evidence
    -- that the charlson CTE produced no row, so ledger_variable_missingness could never
    -- report anything but zero missing Charlson: a fact about the IFNULL, not about the
    -- data. This flag carries that evidence forward, exactly as bmi_missing does.
    (ch.charlson_score IS NULL) AS charlson_missing,
    CASE
      WHEN IFNULL(ch.charlson_score, 0) >= 3 THEN '3_or_more'
      ELSE CAST(IFNULL(ch.charlson_score, 0) AS STRING)
    END AS charlson_ordinal,
    EXTRACT(YEAR FROM e.index_date) AS index_year,
    (e.index_date BETWEEN DATE '2020-03-01' AND DATE '2021-06-30') AS covid_era,
    IFNULL(dvb.device_family_baseline, 'other_or_unknown') AS device_family,
    IF(p.device_model_column = '', 'unavailable', 'device_table') AS device_family_source,
    (IFNULL(dvc.n_device_families, 0) > 1) AS device_changed,

    bl.baseline_steps,
    bl.n_valid_baseline_days,
    bl.baseline_span_days,
    bl.baseline_dow_counts,
    bl.baseline_band_slug,
    bl.meets_baseline_floor,

    -- EIGHT ALTERNATIVE BASELINES ARE CARRIED HERE, NOT SIX. The two week-half medians
    -- and their two valid-day counts are carried alongside the six window and wear
    -- variants, for the same reason those six are: this table is where a sensitivity row
    -- reads its baseline, and a row that had to join the baseline table for four columns
    -- would make the promise this stage is built on false rather than merely incomplete.
    --
    -- THE NULL CONVENTIONS ARE THE ONES baseline WRITES, CARRIED UNCHANGED. The two
    -- medians are NULL, never zero, when their half of the window holds no valid day, by
    -- the same rule as baseline_steps: a zero baseline makes the normalized activity S/B
    -- infinite and the daily deficit silently equal to one on every day, manufacturing a
    -- maximal recovery debt out of missing data, and on these two columns it would do so
    -- precisely on the participants whose wear is concentrated in the other half of the
    -- week, which is a differential error and not a wash. The two counts are INT64, never
    -- null, and zero when the half holds no valid day. Nothing here coalesces either pair.
    --
    -- A SENSITIVITY FITTED ON EITHER MEDIAN RUNS ON ITS OWN DENOMINATOR, AND THE
    -- DENOMINATOR IS TAKEN FROM THE TWO COUNTS. An episode can clear the baseline
    -- adequacy rung on weekdays alone and have no weekend baseline at all, so the set
    -- either median can be fitted on is a DIFFERENT set from the primary's and Table 2
    -- prints that set's own n. ANALYSIS-PLAN 2.2 derives that set from the two COUNTS,
    -- n_valid_baseline_days_weekday of at least 5 AND n_valid_baseline_days_weekend of at
    -- least 2, and NEVER from the two medians being non-null: the count form keeps the
    -- minimum-day rule visible in one place instead of hiding it inside a null test that a
    -- later edit could weaken without anyone noticing. Both counts are carried here so
    -- that the rule can be applied on this table alone.
    bl.baseline_steps_weekday,
    bl.n_valid_baseline_days_weekday,
    bl.baseline_steps_weekend,
    bl.n_valid_baseline_days_weekend,

    bl.baseline_steps_60_15,
    bl.n_valid_baseline_days_60_15,
    bl.baseline_steps_30_1,
    bl.n_valid_baseline_days_30_1,
    bl.baseline_steps_s1, bl.n_valid_baseline_days_s1,
    bl.baseline_steps_s2, bl.n_valid_baseline_days_s2,
    bl.baseline_steps_s3, bl.n_valid_baseline_days_s3,
    bl.baseline_steps_s4, bl.n_valid_baseline_days_s4,

    e.n_analyzable_days_1_35,
    e.n_at_risk_days_1_35,
    SAFE_DIVIDE(e.n_analyzable_days_1_35, 35) AS share_window_observed,
    -- "Near-complete window" is not defined in the plan. It is fixed here at 28 of the
    -- 35 accrual days, that is 80%, so that a Table 1 row cannot be defined after the
    -- distribution is seen.
    (e.n_analyzable_days_1_35 >= 28) AS near_complete_window,
    e.censor_date,
    e.censor_reason,
    -- The last post-discharge day this episode is at risk on, capped at the 90-day
    -- horizon Arm A uses. The accrual window of the primary is days 1 to 35 and is a
    -- subset of it.
    GREATEST(0, LEAST(90, IFNULL(DATE_DIFF(e.censor_date, e.discharge_date, DAY), 90)))
      AS at_risk_last_day,
    p.junction_map
  FROM elig AS e
  CROSS JOIN p
  JOIN `{CDR}.person` AS pe ON pe.person_id = e.person_id
  JOIN `{DERIVED}.baseline` AS bl USING (episode_id)
  LEFT JOIN charlson AS ch USING (episode_id)
  LEFT JOIN bmi_raw    AS b   USING (episode_id)
  LEFT JOIN dev_base   AS dvb USING (episode_id)
  LEFT JOIN dev_change AS dvc USING (episode_id);
  -- @stage-end: features
  END IF;

  -- ===================================================================================
  -- STAGE 11 of 19: drd_daily
  -- The daily deficit panel: one row per analytic episode per POST-DISCHARGE DAY 1 to
  -- 90. The estimand accrues over days 1 to 35; days 36 to 90 are carried because
  -- Figure 2 plots the recovery curve out to day 90 and the display model has its own
  -- knots there. Post-discharge day 1 is the first COMPLETE calendar day after the
  -- index discharge; the discharge day itself is day 0 and is excluded from every
  -- wearable window, because it is a partial inpatient day whose step count mixes two
  -- settings.
  --
  -- THE FOUR-KIND TAXONOMY OF 2.3, AND THE ONE PLACE IT NEEDS TWO COLUMNS.
  -- Inpatient is not exclusive of observed: a readmitted patient who is wearing the
  -- device produces a valid, analyzable, inpatient day, and the plan KEEPS those days
  -- in the primary because a readmission is part of recovery and deleting it would
  -- delete the worst days. day_kind therefore carries the observation status in three
  -- values and is_inpatient carries the setting alongside it, so the "inpatient days
  -- censored" sensitivity is a filter on a flag rather than a rebuild. day_kind_four
  -- reproduces the plan's exclusive four-value taxonomy for the report of 2.3 by
  -- precedence, censored then inpatient then observed then missing.
  --
  -- A missing day is NEVER imputed as zero deficit. A zero deficit is the assertion
  -- that the patient walked at or above their own preoperative baseline that day, which
  -- is the most favourable possible completion of the window and is biased downward
  -- exactly where the deficit is largest. deficit is NULL on a non-analyzable day and
  -- the observation weights of 3.7 do the work instead.
  --
  -- Grain: one row per analytic episode per post-discharge day 1 to 90. Roughly 90 rows
  -- per episode: order of 27,000 to 54,000 rows.
  -- PARTITIONED BY the post-discharge day range and CLUSTERED BY person_id, which is
  -- the one partitioning in this DAG that prunes on a literal predicate, because
  -- WHERE post_discharge_day BETWEEN 1 AND 35 is the dominant downstream filter.
  -- PARTICIPANT-LEVEL.
  -- ===================================================================================
  IF start_ix <= 11 THEN
  -- @stage-begin: drd_daily
  CREATE OR REPLACE TABLE `{DERIVED}.drd_daily`
  PARTITION BY RANGE_BUCKET(post_discharge_day, GENERATE_ARRAY(0, 100, 5))
  CLUSTER BY person_id, episode_id AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  readm AS (
    SELECT
      f.episode_id,
      v.visit_start_date,
      COALESCE(v.visit_end_date, v.visit_start_date) AS visit_end_date
    FROM `{DERIVED}.features` AS f
    CROSS JOIN p
    JOIN `{CDR}.visit_occurrence` AS v
      ON v.person_id = f.person_id
     AND v.visit_concept_id IN UNNEST(p.inpatient_visit_concept_ids)
     AND v.visit_start_date > f.discharge_date
     AND v.visit_start_date <= DATE_ADD(f.discharge_date, INTERVAL 90 DAY)
  ),
  grid AS (
    SELECT
      f.episode_id,
      f.person_id,
      f.los_days,
      f.baseline_steps,
      f.at_risk_last_day,
      day AS post_discharge_day,
      DATE_ADD(f.discharge_date, INTERVAL day DAY) AS calendar_date
    FROM `{DERIVED}.features` AS f
    CROSS JOIN UNNEST(GENERATE_ARRAY(1, 90)) AS day
  ),
  base AS (
    SELECT
      g.episode_id,
      g.person_id,
      g.post_discharge_day,
      g.calendar_date,
      g.los_days + g.post_discharge_day AS postoperative_day,
      EXTRACT(DAYOFWEEK FROM g.calendar_date) AS day_of_week,
      (EXTRACT(DAYOFWEEK FROM g.calendar_date) IN (1, 7)) AS is_weekend,
      fd.steps,
      fd.wear_minutes,
      IFNULL(fd.valid_wear, FALSE)         AS valid_wear,
      IFNULL(fd.valid_wear_s1, FALSE)      AS valid_wear_s1,
      IFNULL(fd.valid_wear_s2, FALSE)      AS valid_wear_s2,
      IFNULL(fd.valid_wear_s3, FALSE)      AS valid_wear_s3,
      IFNULL(fd.valid_wear_s4, FALSE)      AS valid_wear_s4,
      (g.post_discharge_day > g.at_risk_last_day) AS is_censored,
      (IFNULL(fd.is_analyzable, FALSE) AND g.post_discharge_day <= g.at_risk_last_day)
        AS is_analyzable,
      EXISTS(SELECT 1 FROM readm AS r
             WHERE r.episode_id = g.episode_id
               AND g.calendar_date BETWEEN r.visit_start_date AND r.visit_end_date)
        AS is_inpatient,
      g.baseline_steps,
      (g.post_discharge_day BETWEEN 1 AND 35) AS in_accrual_window,
      -- Sensitivity ladder row 1, the protocol's own window: postoperative days 8 to
      -- 42, expressed in post-discharge time. Both windows are 35 days long, so the
      -- estimand's scale and its bound at 35 are identical under either.
      ((g.los_days + g.post_discharge_day) BETWEEN 8 AND 42) AS in_pod_anchored_window
    FROM grid AS g
    LEFT JOIN `{DERIVED}.fitbit_daily` AS fd
      ON fd.person_id = g.person_id AND fd.activity_date = g.calendar_date
  )
  SELECT
    b.episode_id,
    b.person_id,
    b.post_discharge_day,
    b.postoperative_day,
    b.calendar_date,
    b.day_of_week,
    b.is_weekend,
    b.steps,
    b.wear_minutes,
    b.valid_wear,
    b.valid_wear_s1, b.valid_wear_s2, b.valid_wear_s3, b.valid_wear_s4,
    b.is_analyzable,
    b.is_censored,
    b.is_inpatient,
    b.in_accrual_window,
    b.in_pod_anchored_window,
    CASE
      WHEN b.is_censored   THEN 'censored'
      WHEN b.is_analyzable THEN 'observed'
      ELSE 'missing'
    END AS day_kind,
    CASE
      WHEN b.is_censored   THEN 'censored'
      WHEN b.is_inpatient  THEN 'inpatient'
      WHEN b.is_analyzable THEN 'observed'
      ELSE 'missing'
    END AS day_kind_four,
    IF(b.is_analyzable, SAFE_DIVIDE(b.steps, b.baseline_steps), NULL) AS normalized_activity,
    IF(b.is_analyzable, GREATEST(0, 1 - SAFE_DIVIDE(b.steps, b.baseline_steps)), NULL) AS deficit,
    -- Sensitivity ladder row 10: the same quantity without the max(0, .) truncation, so
    -- days above baseline offset days below.
    IF(b.is_analyzable, 1 - SAFE_DIVIDE(b.steps, b.baseline_steps), NULL) AS deficit_untruncated,
    -- The observation model's lagged wear fraction (3.7). The lag is STRICT: the window
    -- is 7 PRECEDING to 1 PRECEDING, so the observation model can never condition on
    -- the very day it is weighting. It is null on post-discharge day 1 and partial
    -- through day 7 by construction, because the plan defines the lag over
    -- post-discharge days.
    AVG(IF(b.valid_wear, 1.0, 0.0)) OVER (
      PARTITION BY b.episode_id ORDER BY b.post_discharge_day
      ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS lagged_wear_fraction,
    p.junction_map
  FROM base AS b
  CROSS JOIN p;
  -- @stage-end: drd_daily
  END IF;

  -- ===================================================================================
  -- STAGE 12 of 19: events
  -- Arm A's outcome (4.1): an EHR-recorded post-discharge acute-care encounter within
  -- 90 days, meaning an emergency department visit or a new inpatient admission
  -- beginning after discharge from the index surgical encounter. An emergency visit
  -- followed by same-day admission collapses to ONE event. The manuscript says
  -- "acute-care encounter", never "unplanned readmission" and never "complication".
  --
  -- The visit_concept_id values are ENUMERATED against the CDR's own distribution and
  -- arrive as procedure parameters. Nothing here assumes 9203 or 9201.
  --
  -- At least 30 postoperative Fitbit days are NOT required, because that restriction
  -- would create selection and immortal-time bias by excluding early events and
  -- patients whose adherence declined during deterioration.
  --
  -- Every event is kept, with event_rank, and is_first_event marks the one the ladder
  -- counts. The later ones exist so that the prespecified secondary admitting repeat
  -- events does not need a second build.
  --
  -- Grain: one row per acute-care encounter date per analytic episode. Order of 100 to
  -- 400 rows, and the feasibility gate is a count over is_first_event.
  -- PARTICIPANT-LEVEL.
  -- ===================================================================================
  IF start_ix <= 12 THEN
  -- @stage-begin: events
  CREATE OR REPLACE TABLE `{DERIVED}.events`
  CLUSTER BY person_id AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  enc AS (
    SELECT
      f.episode_id,
      f.person_id,
      f.discharge_date,
      f.baseline_steps,
      v.visit_occurrence_id,
      v.visit_start_date AS event_date,
      DATE_DIFF(v.visit_start_date, f.discharge_date, DAY) AS event_post_discharge_day,
      (v.visit_concept_id IN UNNEST(p.ed_visit_concept_ids))        AS is_ed,
      (v.visit_concept_id IN UNNEST(p.inpatient_visit_concept_ids)) AS is_inpatient,
      -- The same elective proxy as attrition rung 4, and labelled as one for the same
      -- reason: an admission carrying scheduled or elective wording on the admission
      -- date is not an acute-care event.
      COALESCE(REGEXP_CONTAINS(LOWER(IFNULL(v.visit_source_value, '')), r'elect|sched'), FALSE)
        AS elective_admission
    FROM `{DERIVED}.features` AS f
    CROSS JOIN p
    JOIN `{CDR}.visit_occurrence` AS v
      ON v.person_id = f.person_id
     AND (v.visit_concept_id IN UNNEST(p.ed_visit_concept_ids)
          OR v.visit_concept_id IN UNNEST(p.inpatient_visit_concept_ids))
     AND v.visit_start_date > f.discharge_date
     AND DATE_DIFF(v.visit_start_date, f.discharge_date, DAY) <= f.at_risk_last_day
  ),
  -- One event per episode per date. An emergency visit and an admission on the same
  -- date are one clinical episode of care, not two events.
  collapsed AS (
    SELECT
      episode_id,
      person_id,
      ANY_VALUE(discharge_date)  AS discharge_date,
      ANY_VALUE(baseline_steps)  AS baseline_steps,
      event_date,
      ANY_VALUE(event_post_discharge_day) AS event_post_discharge_day,
      MIN(visit_occurrence_id)   AS visit_occurrence_id,
      CASE
        WHEN LOGICAL_OR(is_ed) AND LOGICAL_OR(is_inpatient) THEN 'ed_then_inpatient'
        WHEN LOGICAL_OR(is_ed)                              THEN 'emergency_department'
        ELSE 'inpatient'
      END AS event_kind,
      LOGICAL_AND(elective_admission) AS elective_admission_excluded
    FROM enc
    GROUP BY episode_id, person_id, event_date
  ),
  kept AS (
    SELECT * FROM collapsed WHERE NOT elective_admission_excluded
  ),
  -- The proximal exposure window (4.2). Every day in it must be a POST-DISCHARGE day:
  -- post-discharge day 1 is the first complete day after discharge, so a window day
  -- falling on or before the discharge date is not eligible. That single requirement is
  -- what structurally deletes events on post-discharge days 1 to 4, which is attrition
  -- rung 18 and is never folded into a generic insufficient-wearable-data row.
  win AS (
    SELECT
      k.episode_id,
      k.event_date,
      `{DERIVED}.exact_median_int`(ARRAY_AGG(
         IF(DATE_DIFF(fd.activity_date, k.event_date, DAY) BETWEEN -5 AND -3
            AND DATE_DIFF(fd.activity_date, k.discharge_date, DAY) >= 1
            AND fd.valid_wear AND fd.steps IS NOT NULL, fd.steps, NULL) IGNORE NULLS))
        AS proximal_median_steps,
      COUNTIF(DATE_DIFF(fd.activity_date, k.event_date, DAY) BETWEEN -5 AND -3
              AND DATE_DIFF(fd.activity_date, k.discharge_date, DAY) >= 1
              AND fd.valid_wear AND fd.steps IS NOT NULL) AS n_valid_days_in_window,
      COUNTIF(DATE_DIFF(fd.activity_date, k.event_date, DAY) BETWEEN -5 AND -3
              AND DATE_DIFF(fd.activity_date, k.discharge_date, DAY) >= 1) AS n_eligible_days_in_window,
      AVG(IF(DATE_DIFF(fd.activity_date, k.event_date, DAY) BETWEEN -5 AND -3
             AND DATE_DIFF(fd.activity_date, k.discharge_date, DAY) >= 1,
             SAFE_DIVIDE(IFNULL(fd.wear_minutes, 0), 1440), NULL)) AS wear_fraction,
      -- Secondary 24-hour landmark: days E-3 through E-1.
      `{DERIVED}.exact_median_int`(ARRAY_AGG(
         IF(DATE_DIFF(fd.activity_date, k.event_date, DAY) BETWEEN -3 AND -1
            AND DATE_DIFF(fd.activity_date, k.discharge_date, DAY) >= 1
            AND fd.valid_wear AND fd.steps IS NOT NULL, fd.steps, NULL) IGNORE NULLS))
        AS proximal_median_steps_24h,
      COUNTIF(DATE_DIFF(fd.activity_date, k.event_date, DAY) BETWEEN -3 AND -1
              AND DATE_DIFF(fd.activity_date, k.discharge_date, DAY) >= 1
              AND fd.valid_wear AND fd.steps IS NOT NULL) AS n_valid_days_in_window_24h,
      -- The tier 2 reference window: the 7-day median over days E-12 to E-6.
      `{DERIVED}.exact_median_int`(ARRAY_AGG(
         IF(DATE_DIFF(fd.activity_date, k.event_date, DAY) BETWEEN -12 AND -6
            AND DATE_DIFF(fd.activity_date, k.discharge_date, DAY) >= 1
            AND fd.valid_wear AND fd.steps IS NOT NULL, fd.steps, NULL) IGNORE NULLS))
        AS reference_median_steps,
      COUNTIF(DATE_DIFF(fd.activity_date, k.event_date, DAY) BETWEEN -12 AND -6
              AND DATE_DIFF(fd.activity_date, k.discharge_date, DAY) >= 1
              AND fd.valid_wear AND fd.steps IS NOT NULL) AS n_valid_days_in_reference,
      -- The negative-control window of 4.8: days E-14 to E-8.
      `{DERIVED}.exact_median_int`(ARRAY_AGG(
         IF(DATE_DIFF(fd.activity_date, k.event_date, DAY) BETWEEN -14 AND -8
            AND DATE_DIFF(fd.activity_date, k.discharge_date, DAY) >= 1
            AND fd.valid_wear AND fd.steps IS NOT NULL, fd.steps, NULL) IGNORE NULLS))
        AS negative_control_median_steps
    FROM kept AS k
    LEFT JOIN `{DERIVED}.fitbit_daily` AS fd
      ON fd.person_id = k.person_id
     AND fd.activity_date BETWEEN DATE_SUB(k.event_date, INTERVAL 14 DAY)
                              AND DATE_SUB(k.event_date, INTERVAL 1 DAY)
    GROUP BY k.episode_id, k.event_date
  )
  SELECT
    FORMAT('%s-%s', k.episode_id, FORMAT_DATE('%Y%m%d', k.event_date)) AS event_id,
    k.episode_id,
    k.person_id,
    k.event_date,
    k.event_post_discharge_day,
    k.event_kind,
    k.visit_occurrence_id,
    ROW_NUMBER() OVER (PARTITION BY k.episode_id ORDER BY k.event_date) AS event_rank,
    (ROW_NUMBER() OVER (PARTITION BY k.episode_id ORDER BY k.event_date) = 1) AS is_first_event,
    DATE_SUB(k.event_date, INTERVAL 3 DAY) AS landmark_date,
    k.event_post_discharge_day - 3         AS landmark_post_discharge_day,
    EXTRACT(DAYOFWEEK FROM DATE_SUB(k.event_date, INTERVAL 3 DAY)) AS landmark_day_of_week,
    IFNULL(w.n_valid_days_in_window, 0)    AS n_valid_days_in_window,
    IFNULL(w.n_eligible_days_in_window, 0) AS n_eligible_days_in_window,
    (IFNULL(w.n_valid_days_in_window, 0) >= 2) AS has_computable_landmark,
    -- Attrition rung 18 counts on THIS column, not on has_computable_landmark. An event
    -- whose window carries fewer than two POST-DISCHARGE days is structurally
    -- uncomputable: it is a definitional problem, not a missing-data one, and it is
    -- exactly the set of events on post-discharge days 1 to 4. An event on day 5 or
    -- later whose eligible days simply were not worn is a DATA condition, stays in the
    -- risk set, and enters the model through no_computable_step_signal instead (4.4).
    (IFNULL(w.n_eligible_days_in_window, 0) < 2) AS structurally_uncomputable_landmark,
    -- The co-primary exposure of 4.4, and the DATA condition only, under the same name and
    -- the same meaning it carries in `landmark_daily` and `risk_sets`. Requiring a
    -- computable ratio at the landmark deletes preferentially the sickest windows, and
    -- conditioning on a common consequence of exposure and outcome is collider
    -- stratification, so an event whose window held its 2 post-discharge days but was not
    -- worn stays in the risk set as `N = 1`. An event whose window never held 2
    -- post-discharge days is a calendar fact rather than a wear fact and is NOT `N`: it
    -- carries the definitional flag above INSTEAD OF this one, and the two counts are
    -- never summed. A single "no computable landmark" number would be the sum of an
    -- exposure and an exclusion, and no reader could take it apart again afterwards.
    (IFNULL(w.n_eligible_days_in_window, 0) >= 2
     AND IFNULL(w.n_valid_days_in_window, 0) < 2) AS no_computable_step_signal,
    3 - IFNULL(w.n_valid_days_in_window, 0)   AS n_missing_days_in_window,
    SAFE_DIVIDE(w.proximal_median_steps, k.baseline_steps)     AS r72,
    SAFE_DIVIDE(w.proximal_median_steps_24h, k.baseline_steps) AS r72_24h,
    SAFE_DIVIDE(w.reference_median_steps, k.baseline_steps)    AS r_reference_7day,
    SAFE_DIVIDE(w.negative_control_median_steps, k.baseline_steps) AS r_negative_control,
    LN(NULLIF(SAFE_DIVIDE(w.proximal_median_steps, w.reference_median_steps), 0))
      AS local_step_deterioration,
    w.wear_fraction,
    p.junction_map
  FROM kept AS k
  CROSS JOIN p
  LEFT JOIN win AS w ON w.episode_id = k.episode_id AND w.event_date = k.event_date;
  -- @stage-end: events
  END IF;

  -- ===================================================================================
  -- STAGE 13 of 19: landmark_daily
  -- THE FULL-COHORT, DAY-INDEXED LANDMARK PANEL, and the reason it exists is the
  -- collider correction of ANALYSIS-PLAN 4.4.
  --
  -- The plan promotes "no computable step signal" to a CO-PRIMARY EXPOSURE and specifies
  -- inverse-probability-of-observation weighting alongside it, on the reasoning that wear
  -- is plausibly caused BOTH by declining activity AND by the illness that generates the
  -- outcome. If that is right, then requiring a computable landmark deletes exactly the
  -- sickest windows, and the deletion is not random: conditioning on a common consequence
  -- of exposure and outcome is collider stratification.
  --
  -- TESTING THAT REASONING NEEDS A DAY-INDEXED PANEL OVER THE WHOLE COHORT. Before this
  -- stage existed the with-versus-without comparison could only be made at the SAMPLED
  -- risk sets, which carries a sampling caveat, and inside `events`, which holds only
  -- event dates and reports chiefly on first events. Neither answers "on an ordinary
  -- episode-day, how often was a landmark computable, and did an event follow?" This
  -- table answers it on every analytic episode and every post-discharge day, including
  -- the days nobody was sampled at and the episodes that never had an event.
  --
  -- THE TWO LANDMARK CONDITIONS STAY SEPARATE HERE, WITH THE SAME NAMES AND THE SAME
  -- MEANINGS THEY CARRY IN `events` AND `risk_sets` (ANALYSIS-PLAN 4.4).
  --   has_computable_landmark             at least 2 VALID days in the window.
  --   no_computable_step_signal           the DATA condition, and ONLY the data
  --                                       condition: the window holds at least 2
  --                                       post-discharge days but fewer than 2 of them
  --                                       were worn. This is `N`, the co-primary
  --                                       exposure, and the window STAYS.
  --   structurally_uncomputable_landmark  the DEFINITIONAL condition: the window holds
  --                                       fewer than 2 post-discharge days at all,
  --                                       equivalently a landmark day of 1 or less,
  --                                       equivalently a post-discharge day of 4 or less.
  --                                       It carries NO `N` and is attrition rung 18.
  -- THE THREE PARTITION THE PANEL: every episode-day is in exactly one of them, because
  -- valid days are a subset of eligible days. THEIR COUNTS ARE NEVER SUMMED, here or on
  -- either of the other two surfaces. Note that NOT has_computable_landmark is the UNION
  -- of the last two and is not the data condition; the data condition is the middle column
  -- and nothing else. Merging them would silently delete the very windows this table
  -- exists to keep, which is the exact bias the co-primary exposure was introduced to
  -- avoid, and a single "no computable landmark" number would be the sum of an exposure
  -- and an exclusion that no reader could take apart again afterwards.
  --
  -- IT IS A THREE-DAY-OFFSET SELF-JOIN OF drd_daily AND IS THEREFORE CHEAP. The window
  -- for post-discharge day d is days d minus 5, d minus 4 and d minus 3, so the join key
  -- is a three-day range on a derived table that is already materialized. Because
  -- drd_daily's grid STARTS at post-discharge day 1, a window day that is not a
  -- post-discharge day simply has no row to match. That is what makes
  -- n_eligible_days_in_window structural rather than a second copy of the rule in
  -- `events` that could later drift away from it.
  --
  -- THE EARLY-LANDMARK WEIGHT PROBLEM (4.4, and the reason for five of the columns below).
  -- A risk set matched at post-discharge day d has its landmark at d minus 3, so a set
  -- matched on day 3 or earlier has a landmark on day 0 or before, where drd_daily has no
  -- row at all; and a set matched on day 4 has its landmark on day 1, where drd_daily has
  -- a row but lagged_wear_fraction is null by construction, because the lag is defined
  -- over POST-DISCHARGE days and day 1 has none preceding it. The observation weights of
  -- 3.7 therefore have NO INPUT at any matched day of 4 or earlier. This stage does not
  -- decide what to do about that, because the rule is a prespecification question and not
  -- a build question. It supplies both of the things a rule could need:
  --   landmark_lagged_wear_fraction            the plan's own quantity, carried forward
  --                                            from drd_daily at the landmark day, NULL
  --                                            exactly where the weight has no input, so
  --                                            the affected members are COUNTABLE rather
  --                                            than merely describable;
  --   landmark_lagged_wear_fraction_wearable   the same fraction taken over the WEARABLE
  --                                            grid, the seven calendar days before the
  --                                            landmark date, which exists before
  --                                            post-discharge day 1 because fitbit_daily
  --                                            reaches back to index day minus 60.
  -- THE TWO ARE NOT THE SAME QUANTITY and one may not be silently substituted for the
  -- other: the wearable-grid version can average over inpatient days and, at an early
  -- landmark, over PREOPERATIVE days, where wear behaviour is a different thing. Which
  -- one the weight model uses, or whether an early landmark instead takes a marginal
  -- weight, is named in ANALYSIS-PLAN 4.4 and is reported with its own denominator.
  --
  -- Grain: one row per analytic episode per post-discharge day 1 to 90, the same grid as
  -- drd_daily. Roughly 27,000 to 54,000 rows. PARTICIPANT-LEVEL.
  -- ===================================================================================
  IF start_ix <= 13 THEN
  -- @stage-begin: landmark_daily
  CREATE OR REPLACE TABLE `{DERIVED}.landmark_daily`
  PARTITION BY RANGE_BUCKET(post_discharge_day, GENERATE_ARRAY(0, 100, 5))
  CLUSTER BY person_id, episode_id AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  -- One row per episode per event DATE. `events` has already collapsed an emergency
  -- visit and a same-day admission into a single event, so this cannot double count a
  -- day, and the aggregation here only guards against a repeat event sharing a date.
  ev AS (
    SELECT
      episode_id,
      event_post_discharge_day   AS post_discharge_day,
      TRUE                       AS is_event,
      LOGICAL_OR(is_first_event) AS is_first_event
    FROM `{DERIVED}.events`
    GROUP BY episode_id, event_post_discharge_day
  ),
  -- The three-day offset. `w` is the window row, `d` is the day it is a landmark window
  -- for. The valid-day rule is the one `events` uses, valid wear AND a non-null step
  -- count, because a heart-rate day with no step record cannot contribute to a median of
  -- steps and counting it would inflate the computable share.
  win AS (
    SELECT
      d.episode_id,
      ANY_VALUE(d.person_id)     AS person_id,
      d.post_discharge_day,
      ANY_VALUE(d.is_censored)   AS is_censored,
      ANY_VALUE(d.calendar_date) AS day_date,
      COUNTIF(w.valid_wear AND w.steps IS NOT NULL) AS n_valid_days_in_window,
      -- Structural, not a second rule: drd_daily's grid begins at post-discharge day 1,
      -- so a window day before that has no row and is not counted.
      COUNT(w.post_discharge_day)                   AS n_eligible_days_in_window,
      -- The plan's own observation-weight input, read at the landmark day itself. Null
      -- when the landmark falls on post-discharge day 1 or earlier.
      MAX(IF(w.post_discharge_day = d.post_discharge_day - 3, w.lagged_wear_fraction, NULL))
                                                    AS landmark_lagged_wear_fraction
    FROM `{DERIVED}.drd_daily` AS d
    LEFT JOIN `{DERIVED}.drd_daily` AS w
      ON w.episode_id = d.episode_id
     AND w.post_discharge_day BETWEEN d.post_discharge_day - 5 AND d.post_discharge_day - 3
    GROUP BY d.episode_id, d.post_discharge_day
  ),
  -- The wearable-grid alternative. The landmark date is day_date minus 3, so the seven
  -- calendar days STRICTLY before it are day_date minus 10 through day_date minus 4. The
  -- lag is strict for the same reason it is strict in drd_daily: a weight may never
  -- condition on the day it is weighting.
  lagged AS (
    SELECT
      w.episode_id,
      w.post_discharge_day,
      AVG(IF(fd.valid_wear, 1.0, 0.0)) AS landmark_lagged_wear_fraction_wearable,
      COUNT(fd.activity_date)          AS n_days_behind_landmark_on_wearable_grid
    FROM win AS w
    LEFT JOIN `{DERIVED}.fitbit_daily` AS fd
      ON fd.person_id = w.person_id
     AND fd.activity_date BETWEEN DATE_SUB(w.day_date, INTERVAL 10 DAY)
                              AND DATE_SUB(w.day_date, INTERVAL 4 DAY)
    GROUP BY w.episode_id, w.post_discharge_day
  )
  SELECT
    w.episode_id,
    w.person_id,
    w.post_discharge_day,
    w.post_discharge_day - 3                AS landmark_post_discharge_day,
    w.is_censored,
    w.n_valid_days_in_window,
    w.n_eligible_days_in_window,
    (w.n_valid_days_in_window >= 2)         AS has_computable_landmark,
    (w.n_eligible_days_in_window < 2)       AS structurally_uncomputable_landmark,
    -- The co-primary exposure of 4.4, and the DATA condition only, under the same name and
    -- the same meaning it carries in `events` and `risk_sets`, so the panel, the event
    -- table and the matched sets compare without a translation. An episode-day whose window
    -- never held 2 post-discharge days carries the definitional flag above INSTEAD OF this
    -- one, and the two counts are never summed.
    (w.n_eligible_days_in_window >= 2
     AND w.n_valid_days_in_window < 2)      AS no_computable_step_signal,
    w.landmark_lagged_wear_fraction,
    (w.landmark_lagged_wear_fraction IS NOT NULL)
                                            AS landmark_weight_input_available,
    ((w.post_discharge_day - 3) < 1)        AS landmark_before_post_discharge_day_one,
    l.landmark_lagged_wear_fraction_wearable,
    l.n_days_behind_landmark_on_wearable_grid,
    IFNULL(e.is_event, FALSE)               AS is_event_day,
    IFNULL(e.is_first_event, FALSE)         AS is_first_event_day,
    p.junction_map
  FROM win AS w
  CROSS JOIN p
  LEFT JOIN lagged AS l
    ON l.episode_id = w.episode_id AND l.post_discharge_day = w.post_discharge_day
  LEFT JOIN ev AS e
    ON e.episode_id = w.episode_id AND e.post_discharge_day = w.post_discharge_day;
  -- @stage-end: landmark_daily

  -- THE PANEL MUST REPRODUCE `events` WHERE THE TWO OVERLAP. At an event's own
  -- post-discharge day this table computes the same proximal window `events` computes, by
  -- the same rule, from a different source: `events` counts days out of fitbit_daily and
  -- this stage counts them out of drd_daily. A disagreement means one of the two window
  -- definitions has drifted, and the full-cohort comparison this table exists for would
  -- then be answering a different question from the one the risk sets answer, which is
  -- precisely the confusion a collider correction cannot survive.
  IF (SELECT COUNT(*)
      FROM `{DERIVED}.events` AS e
      JOIN `{DERIVED}.landmark_daily` AS l
        ON l.episode_id = e.episode_id
       AND l.post_discharge_day = e.event_post_discharge_day
      WHERE l.n_valid_days_in_window != e.n_valid_days_in_window
         OR l.n_eligible_days_in_window != e.n_eligible_days_in_window
         OR l.has_computable_landmark != e.has_computable_landmark
         OR l.structurally_uncomputable_landmark != e.structurally_uncomputable_landmark) > 0 THEN
    RAISE USING MESSAGE = 'landmark_daily and events disagree about the proximal window at an event date. Both compute the E minus 5 to E minus 3 window under the same rule, events out of fitbit_daily and landmark_daily out of drd_daily, so a disagreement means one definition has drifted or one of the two tables is stale from an earlier build. Rebuild from start_stage = drd_daily rather than reconciling the two by hand.';
  END IF;

  -- The structural flag must be a statement about the CALENDAR and nothing else. Fewer
  -- than two post-discharge days in the window happens for post-discharge days 1 to 4 and
  -- for no other day, which is the six-row derivation of ANALYSIS-PLAN 4.3 checked on
  -- every episode-day rather than only at event dates the way rung 18 checks it.
  IF (SELECT COUNTIF(structurally_uncomputable_landmark != (post_discharge_day <= 4))
      FROM `{DERIVED}.landmark_daily`) > 0 THEN
    RAISE USING MESSAGE = 'The structurally uncomputable landmark flag in landmark_daily does not agree with post-discharge day 1 to 4. That flag is arithmetic on the post-discharge grid, so a disagreement means drd_daily no longer carries one row per analytic episode per post-discharge day 1 to 90 and every window count in this panel is suspect.';
  END IF;
  END IF;

  -- ===================================================================================
  -- STAGE 14 of 19: risk_sets
  -- Incidence-density sampled matched sets for Arm A (4.5). Under-specified risk-set
  -- sampling biases away from the null, chiefly by drawing controls only from
  -- participants who never have an event, which conditions the control pool on the
  -- future. Every degree of freedom is closed here:
  --   post-discharge day is the SINGLE time scale, not calendar time;
  --   a participant may be a control at one landmark and a case later, and future case
  --     status does not disqualify them, which is the rule that makes this a risk-set
  --     design rather than a case-control study of survivors;
  --   calendar year is a covariate and NOT a matching factor;
  --   up to 5 controls per case;
  --   at most 3 control landmarks from any one participant across the whole study.
  --
  -- SEEDED FARM_FINGERPRINT, NEVER A NONDETERMINISTIC RANDOM ORDERING. A random draw
  -- would give a different matched set every time the procedure is called, so the odds ratio would move between sessions
  -- for no reason a reader could see, and a resumed session could not reproduce the
  -- number in a draft. FARM_FINGERPRINT over a fixed salt, the seed, the set id and the
  -- member id is a deterministic pseudo-random ordering: identical sets, this session
  -- and the next, on any machine.
  --
  -- THE TWO CAPS ARE APPLIED IN THIS ORDER, AND THE ORDER IS A REAL CHOICE.
  -- First the per-set cap of 5, ranking by fingerprint within the set; then the
  -- per-participant cap of 3, ranking that participant's SURVIVING selections by
  -- fingerprint. Applying the participant cap first would spend a prolific
  -- participant's three slots on sets where they would not have been drawn anyway.
  -- This is NOT a sequential greedy assignment, which one pass of SQL cannot express;
  -- it is a fully determined two-pass rule, and its consequence is that some sets end
  -- with fewer than 5 controls. That is expected, and the distribution is exactly what
  -- ledger_matched_set_sizes reports.
  --
  -- The relaxation ladder of 4.7 depends only on RISK-SET SIZE, which is a count, never
  -- on an outcome or an estimate. The three rungs are nested, so the counts are taken
  -- once and the chosen rung is the strictest one leaving at least 2 eligible controls.
  --
  -- THE TWO LANDMARK CONDITIONS ARE SEPARATE HERE, WITH THE SAME NAMES AND THE SAME
  -- MEANINGS THEY CARRY IN `events` AND `landmark_daily` (ANALYSIS-PLAN 4.4).
  --   has_computable_landmark             at least 2 VALID days in the window.
  --   no_computable_step_signal           the DATA condition, and ONLY the data
  --                                       condition: the window holds at least 2
  --                                       post-discharge days but fewer than 2 of them
  --                                       were worn. This is `N`, the co-primary
  --                                       exposure, and the member STAYS.
  --   structurally_uncomputable_landmark  the DEFINITIONAL condition: the window holds
  --                                       fewer than 2 post-discharge days at all,
  --                                       equivalently a landmark day of 1 or less,
  --                                       equivalently a matched day of 4 or less. The
  --                                       member carries NO `N` and LEAVES.
  -- THEIR COUNTS ARE NEVER SUMMED, here or on either of the other two surfaces. A single
  -- "no computable landmark" number would be the sum of a data condition that is an
  -- exposure and a definitional condition that is an exclusion, and no reader could take
  -- it apart again afterwards.
  --
  -- WHY THE DEFINITIONAL CONDITION MAY NOT SIT INSIDE no_computable_step_signal. `N`
  -- exists to capture sick people who stopped wearing the device. A window that is
  -- uncomputable because it STRADDLES DISCHARGE is uncomputable for calendar reasons
  -- that have nothing to do with the participant's illness or behaviour, and it is a
  -- deterministic function of post-discharge day, which is already this design's single
  -- time scale, already matched on and already conditioned on. Folding it into `N` would
  -- put a calendar artefact inside the coefficient that exists to measure informative
  -- non-wear, and it would do so in the direction that matters, because the members it
  -- adds are the earliest ones.
  --
  -- SUCH A MEMBER IS DROPPED AND COUNTED, NOT SILENTLY FILTERED OUT. Every case here is
  -- at post-discharge day 5 or later, because `cases` reads only events that survived
  -- rung 18. The day-of-week relaxation of 4.7 can still put a CONTROL at post-discharge
  -- day 3 or 4, and that control cannot leave at rung 18, because rung 18 is an EVENT
  -- rung and a sampled control is not an event. It is therefore admitted by the
  -- relaxation, drawn under both caps, and then dropped from its risk set as a member,
  -- carrying structurally_uncomputable_landmark and a NULL r72 so that the drop is
  -- visible and countable. 04_features.py counts it, split by the two routes of 4.4, and
  -- counts the sets that lose EVERY control that way. Refusing such a control at the
  -- candidate stage instead would make both of those counts structurally zero, which is
  -- the silent exclusion the plan exists to prevent.
  --
  -- Grain: one row per matched set per member, cases included. Order of 10^3 rows.
  -- PARTICIPANT-LEVEL.
  -- ===================================================================================
  IF start_ix <= 14 THEN
  -- @stage-begin: risk_sets
  CREATE OR REPLACE TABLE `{DERIVED}.risk_sets`
  CLUSTER BY person_id AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  cases AS (
    SELECT
      ev.event_id AS set_id,
      ev.episode_id,
      ev.person_id,
      ev.event_date,
      ev.event_post_discharge_day AS matched_day,
      ev.landmark_day_of_week
    FROM `{DERIVED}.events` AS ev
    WHERE ev.is_first_event AND NOT ev.structurally_uncomputable_landmark
  ),
  -- Every analytic episode is a candidate control at every post-discharge day it is
  -- still at risk on and has not yet had an encounter on.
  pool AS (
    SELECT
      f.episode_id,
      f.person_id,
      f.discharge_date,
      f.at_risk_last_day,
      (SELECT MIN(e2.event_post_discharge_day)
       FROM `{DERIVED}.events` AS e2
       WHERE e2.episode_id = f.episode_id) AS first_event_day
    FROM `{DERIVED}.features` AS f
  ),
  -- Every (case, control, offset) triple, with the offset ranging over the widest
  -- relaxation rung. Written as a plain cross join with the arithmetic in the SELECT and
  -- the filtering in a wrapping layer, rather than as an UNNEST of a computed array,
  -- because a correlated UNNEST of an expression is a construct an engine is free to
  -- refuse and there is nothing to gain from it here.
  cand_raw AS (
    SELECT
      c.set_id,
      c.matched_day               AS case_matched_day,
      c.episode_id                AS case_episode_id,
      c.person_id                 AS case_person_id,
      c.event_date                AS case_event_date,
      c.landmark_day_of_week      AS case_landmark_day_of_week,
      pl.episode_id               AS control_episode_id,
      pl.person_id                AS control_person_id,
      pl.discharge_date           AS control_discharge_date,
      pl.at_risk_last_day         AS control_at_risk_last_day,
      pl.first_event_day          AS control_first_event_day,
      c.matched_day + offset_days AS control_matched_day
    FROM cases AS c
    JOIN pool AS pl
      ON pl.episode_id != c.episode_id
    CROSS JOIN UNNEST(GENERATE_ARRAY(-2, 2)) AS offset_days
  ),
  -- Rung eligibility. The rungs are nested by construction: same day and same day of
  -- week implies within 2 days and the same weekend class, which implies within 2 days.
  --
  -- THE FLOOR IS POST-DISCHARGE DAY 1, NOT 5, AND THE DIFFERENCE IS THE WHOLE OF 4.4's
  -- SECOND RULE. The first eligible landmark is post-discharge day 2, belonging to an
  -- event on day 5, so a control at a matched day of 4 or less has no exposure window at
  -- all. That is the DEFINITIONAL condition, and the plan admits such a control here and
  -- drops it as a MEMBER below rather than refusing it as a candidate: the drop and the
  -- sets it empties are counts the plan obliges, and a floor of 5 written here would make
  -- every one of those counts structurally zero while looking like a definition. The
  -- floor that remains is the only one that is not a matching rule at all: a control must
  -- sit on a post-discharge day, and post-discharge day 1 is the first of them.
  cand_rung AS (
    SELECT
      cr.*,
      EXTRACT(DAYOFWEEK FROM DATE_ADD(cr.control_discharge_date,
                                      INTERVAL cr.control_matched_day - 3 DAY))
        AS control_landmark_day_of_week,
      (cr.control_matched_day = cr.case_matched_day
       AND EXTRACT(DAYOFWEEK FROM DATE_ADD(cr.control_discharge_date,
                                           INTERVAL cr.control_matched_day - 3 DAY))
           = cr.case_landmark_day_of_week) AS ok_rung1,
      ((EXTRACT(DAYOFWEEK FROM DATE_ADD(cr.control_discharge_date,
                                        INTERVAL cr.control_matched_day - 3 DAY)) IN (1, 7))
       = (cr.case_landmark_day_of_week IN (1, 7))) AS ok_rung2,
      TRUE AS ok_rung3,
      FARM_FINGERPRINT(FORMAT('%s|%d|%s|%s|%d',
        (SELECT sampling_salt FROM p), (SELECT seed FROM p),
        cr.set_id, cr.control_episode_id, cr.control_matched_day)) AS fingerprint
    FROM cand_raw AS cr
    WHERE cr.control_matched_day >= 1
      AND cr.control_at_risk_last_day >= cr.control_matched_day
      AND (cr.control_first_event_day IS NULL
           OR cr.control_first_event_day > cr.control_matched_day)
  ),
  -- One candidacy per (set, control episode). The STRICTEST rung the pair can satisfy
  -- wins, then the closest post-discharge day, then the fingerprint. Ordering by
  -- closeness first would silently discard a pair that matched on weekday class at an
  -- offset of one while failing it at an offset of zero, which would push the whole set
  -- down a relaxation rung for no reason.
  cand_best AS (
    SELECT * EXCEPT(rn) FROM (
      SELECT
        cr.*,
        ROW_NUMBER() OVER (
          PARTITION BY cr.set_id, cr.control_episode_id
          ORDER BY IF(cr.ok_rung1, 0, 1),
                   IF(cr.ok_rung2, 0, 1),
                   ABS(cr.control_matched_day - cr.case_matched_day),
                   cr.fingerprint) AS rn
      FROM cand_rung AS cr
    )
    WHERE rn = 1
  ),
  rung_pick AS (
    SELECT
      set_id,
      CASE
        WHEN COUNTIF(ok_rung1) >= 2 THEN 1
        WHEN COUNTIF(ok_rung2) >= 2 THEN 2
        ELSE 3
      END AS match_rung
    FROM cand_best
    GROUP BY set_id
  ),
  eligible AS (
    SELECT cb.*, rp.match_rung
    FROM cand_best AS cb
    JOIN rung_pick AS rp USING (set_id)
    WHERE (rp.match_rung = 1 AND cb.ok_rung1)
       OR (rp.match_rung = 2 AND cb.ok_rung2)
       OR (rp.match_rung = 3)
  ),
  -- Cap one: up to 5 controls per case.
  capped_set AS (
    SELECT * EXCEPT(rn_set) FROM (
      SELECT e.*, ROW_NUMBER() OVER (PARTITION BY e.set_id ORDER BY e.fingerprint) AS rn_set
      FROM eligible AS e
    )
    WHERE rn_set <= 5
  ),
  -- Cap two: at most 3 control landmarks from any one participant, across the study.
  capped_person AS (
    SELECT * EXCEPT(rn_person) FROM (
      SELECT cs.*,
             ROW_NUMBER() OVER (PARTITION BY cs.control_person_id ORDER BY cs.fingerprint) AS rn_person
      FROM capped_set AS cs
    )
    WHERE rn_person <= 3
  ),
  members AS (
    SELECT
      c.set_id,
      c.episode_id   AS case_episode_id,
      c.person_id    AS case_person_id,
      c.event_date   AS case_event_date,
      c.matched_day  AS case_matched_day,
      'case'         AS member_role,
      c.episode_id,
      c.person_id,
      c.matched_day  AS member_matched_day,
      1              AS match_rung,
      CAST(NULL AS INT64) AS fingerprint
    FROM cases AS c
    UNION ALL
    SELECT
      cp.set_id,
      cp.case_episode_id,
      cp.case_person_id,
      cp.case_event_date,
      cp.case_matched_day,
      'control',
      cp.control_episode_id,
      cp.control_person_id,
      cp.control_matched_day,
      cp.match_rung,
      cp.fingerprint
    FROM capped_person AS cp
  ),
  -- Exposure at each member's OWN landmark, computed identically for cases and
  -- controls, which is the point of the design: the control contributes the exposure it
  -- had at the same post-discharge day the case had its event.
  member_exposure AS (
    SELECT
      m.set_id,
      m.episode_id,
      `{DERIVED}.exact_median_int`(ARRAY_AGG(
         IF(DATE_DIFF(fd.activity_date, DATE_ADD(f.discharge_date, INTERVAL m.member_matched_day DAY), DAY)
              BETWEEN -5 AND -3
            AND DATE_DIFF(fd.activity_date, f.discharge_date, DAY) >= 1
            AND fd.valid_wear AND fd.steps IS NOT NULL, fd.steps, NULL) IGNORE NULLS))
        AS proximal_median_steps,
      COUNTIF(DATE_DIFF(fd.activity_date, DATE_ADD(f.discharge_date, INTERVAL m.member_matched_day DAY), DAY)
                BETWEEN -5 AND -3
              AND DATE_DIFF(fd.activity_date, f.discharge_date, DAY) >= 1
              AND fd.valid_wear AND fd.steps IS NOT NULL) AS n_valid_days_in_window,
      -- The window days that are POST-DISCHARGE days, worn or not, counted by the same
      -- rule `events` counts them by: fitbit_daily is a dense calendar grid per linked
      -- person, so this is the calendar count and not a second wear rule.
      COUNTIF(DATE_DIFF(fd.activity_date, DATE_ADD(f.discharge_date, INTERVAL m.member_matched_day DAY), DAY)
                BETWEEN -5 AND -3
              AND DATE_DIFF(fd.activity_date, f.discharge_date, DAY) >= 1) AS n_eligible_days_in_window,
      AVG(IF(DATE_DIFF(fd.activity_date, DATE_ADD(f.discharge_date, INTERVAL m.member_matched_day DAY), DAY)
               BETWEEN -5 AND -3
             AND DATE_DIFF(fd.activity_date, f.discharge_date, DAY) >= 1,
             SAFE_DIVIDE(IFNULL(fd.wear_minutes, 0), 1440), NULL)) AS wear_fraction
    FROM members AS m
    JOIN `{DERIVED}.features` AS f ON f.episode_id = m.episode_id
    LEFT JOIN `{DERIVED}.fitbit_daily` AS fd
      ON fd.person_id = m.person_id
     AND fd.activity_date BETWEEN DATE_SUB(DATE_ADD(f.discharge_date, INTERVAL m.member_matched_day DAY), INTERVAL 5 DAY)
                              AND DATE_SUB(DATE_ADD(f.discharge_date, INTERVAL m.member_matched_day DAY), INTERVAL 3 DAY)
    GROUP BY m.set_id, m.episode_id
  ),
  sized AS (
    SELECT set_id, COUNTIF(member_role = 'control') AS set_size
    FROM members GROUP BY set_id
  )
  SELECT
    m.set_id,
    m.case_episode_id,
    m.case_person_id,
    m.case_event_date,
    m.case_matched_day,
    m.member_role,
    m.episode_id,
    m.person_id,
    m.member_matched_day,
    DATE_ADD(f.discharge_date, INTERVAL m.member_matched_day - 3 DAY) AS member_landmark_date,
    m.member_matched_day - 3 AS member_landmark_post_discharge_day,
    EXTRACT(DAYOFWEEK FROM DATE_ADD(f.discharge_date, INTERVAL m.member_matched_day - 3 DAY))
      AS member_landmark_day_of_week,
    m.match_rung,
    s.set_size,
    m.fingerprint,
    IFNULL(me.n_valid_days_in_window, 0)    AS n_valid_days_in_window,
    IFNULL(me.n_eligible_days_in_window, 0) AS n_eligible_days_in_window,
    (IFNULL(me.n_valid_days_in_window, 0) >= 2) AS has_computable_landmark,
    -- The DEFINITIONAL condition, under the same name and the same meaning it carries in
    -- `events` and `landmark_daily`: fewer than 2 POST-DISCHARGE days in the window. A
    -- member carrying it has no exposure window at all, carries no `N`, and is dropped
    -- from its risk set. It cannot leave at rung 18, which is an event rung, so it is
    -- dropped here and counted by 04_features.py off member_landmark_post_discharge_day.
    (IFNULL(me.n_eligible_days_in_window, 0) < 2) AS structurally_uncomputable_landmark,
    -- The co-primary exposure of 4.4, and the DATA condition only. Requiring a computable
    -- ratio at the landmark deletes preferentially the sickest windows, and conditioning
    -- on a common consequence of exposure and outcome is collider stratification, so a
    -- window that holds its 2 post-discharge days but was not worn stays in the risk set
    -- as `N = 1`. A window that never held 2 post-discharge days is a calendar fact
    -- rather than a wear fact and is NOT `N`: it is excluded above, and the two counts
    -- are never summed.
    (IFNULL(me.n_eligible_days_in_window, 0) >= 2
     AND IFNULL(me.n_valid_days_in_window, 0) < 2) AS no_computable_step_signal,
    -- No exposure window means no ratio. Without this a member at matched day 4 would
    -- publish a ratio built from the single post-discharge day its window reaches, and a
    -- reader who forgot the structural flag would fit it as though it were the exposure.
    IF(IFNULL(me.n_eligible_days_in_window, 0) < 2,
       NULL, SAFE_DIVIDE(me.proximal_median_steps, f.baseline_steps)) AS r72,
    me.wear_fraction,
    (m.member_role = 'case') AS is_case,
    p.junction_map
  FROM members AS m
  CROSS JOIN p
  JOIN `{DERIVED}.features` AS f ON f.episode_id = m.episode_id
  JOIN sized AS s USING (set_id)
  LEFT JOIN member_exposure AS me ON me.set_id = m.set_id AND me.episode_id = m.episode_id;
  -- @stage-end: risk_sets

  -- The structural flag must be a statement about the CALENDAR and nothing else, exactly
  -- as it is on the panel. A member's landmark day is its matched day minus 3 and the
  -- window is the three days ending there, so the window holds fewer than two
  -- post-discharge days at a matched day of 4 or less and at no other matched day.
  IF (SELECT COUNTIF(structurally_uncomputable_landmark != (member_matched_day <= 4))
      FROM `{DERIVED}.risk_sets`) > 0 THEN
    RAISE USING MESSAGE = 'The structurally uncomputable landmark flag in risk_sets does not agree with a matched day of 4 or less. That flag is arithmetic on the post-discharge grid and is counted out of fitbit_daily, which is a dense calendar grid per linked person, so a disagreement means fitbit_daily no longer covers every calendar day of the window and every window count in this table is suspect. Rebuild from start_stage = fitbit_daily rather than reconciling the two by hand.';
  END IF;

  -- Every case here came through rung 18, which already removed events on post-discharge
  -- days 1 to 4, so no case row may carry the definitional condition. A case that did
  -- would mean the primary had admitted an event with no exposure window at all.
  IF (SELECT COUNTIF(member_role = 'case' AND structurally_uncomputable_landmark)
      FROM `{DERIVED}.risk_sets`) > 0 THEN
    RAISE USING MESSAGE = 'A case row in risk_sets carries structurally_uncomputable_landmark. Cases are read from events under NOT structurally_uncomputable_landmark, which is attrition rung 18, so this means events and risk_sets disagree about the same window or one of the two tables is stale from an earlier build. Rebuild from start_stage = events.';
  END IF;
  END IF;

  -- ===================================================================================
  -- STAGE 15 of 19: attrition
  -- THE NINETEEN-RUNG LADDER OF ANALYSIS-PLAN 2.6, EXACTLY. This table is the single
  -- authoritative rung list materialized; CLAUDE.md section 4 and EXPORT-CONTRACT.md
  -- sections 3.3 and 7.2 transcribe it and do not extend it, and local/verify.py
  -- asserts SET EQUALITY of the slug column against the plan. The nineteen slug
  -- literals below are the assertion's other side, which is why they are written out
  -- rather than generated.
  --
  -- AN EPISODE IS COUNTED ONCE, AT THE FIRST RUNG IT FAILS. That is what makes the
  -- ladder close, and it is why trauma, malignancy and infection are ONE composite rung
  -- rather than three: an episode can trip more than one at a time, so three rungs would
  -- carry order-dependent counts a reader would misread as prevalences, and at this
  -- cohort size three rungs would very likely produce three suppressed rows where the
  -- composite produces one disclosable one. The per-indication breakdown goes to
  -- ledger_exclusion_reasons, where the rows may overlap and are not a partition.
  --
  -- THE THREE CLOSURE MECHANICS, IMPLEMENTED RATHER THAN APPROXIMATED.
  -- 1. Every EXCLUSION rung asserts n_in - n_dropped = n_out, both sides in one unit.
  -- 2. Step 2 CANNOT assert that, because n_in is persons and n_out is episodes. It
  --    carries a third count, n_carried_forward, in persons, and asserts
  --    n_in - n_dropped = n_carried_forward together with n_out >= n_carried_forward,
  --    since a carried person yields at least one episode. An explicitly labelled
  --    re-basing, never a silent one.
  -- 3. Steps 17 and 19 count EVENTS, carry no n_dropped, and are EXCLUDED from the
  --    global "sum of drops plus the analytic n equals the starting n" assert. Steps 17
  --    to 19 close among themselves: n_out(17) - n_dropped(18) = n_out(19).
  -- A fourth, uniform check runs over all nineteen: n_in(k) = n_out(k - 1). It holds
  -- across both conversions, because a conversion re-bases the unit but not the count.
  --
  -- WHAT closes_exact ACTUALLY TESTS, AND WHERE IT IS EMPTY. READ THIS BEFORE TREATING
  -- THE COLUMN AS EVIDENCE. The four mechanics above state the identities. They are not
  -- all TESTED, because the counts CTE below computes one side of most of them FROM the
  -- other side, and an expression compared against itself cannot fail. Rung by rung:
  --   steps 3 to 15  n_out is DEFINED as n_in - n_dropped, so the rung's own test is
  --                  (n_in - n_dropped) = (n_in - n_dropped). n_in is the running-sum
  --                  window over those same drops, so n_in(k) = n_out(k - 1) is that
  --                  same algebra once more. BOTH CONJUNCTS ARE TAUTOLOGIES.
  --   step 1         n_dropped is DEFINED as n_persons_total - n_persons_with_concept.
  --                  TAUTOLOGY.
  --   step 2         n_dropped is DEFINED as n_persons_with_concept minus
  --                  n_persons_with_episode, so the n_carried_forward identity is a
  --                  tautology, and n_out >= n_carried_forward is COUNT(*) >=
  --                  COUNT(DISTINCT person_id) over one table, which cannot fail either.
  --   step 18        n_out is DEFINED as n_in - n_dropped. TAUTOLOGY.
  --   step 17        n_in is n_analytic, the same tot expression as n_out(16), and the
  --                  rung's own test is n_dropped IS NULL AND n_out >= 0, which a count
  --                  cannot fail. TAUTOLOGY.
  --   step 19        n_in and n_out are both the same tot expression as n_out(18).
  --                  TAUTOLOGY.
  --   step 16        n_in = n_out(15) is THE ONE INDEPENDENT IDENTITY IN THE LADDER. It
  --                  reconciles COUNTIF(is_eligible) against COUNT(*) FROM episodes less
  --                  the first_fail_step histogram: two different aggregations that a
  --                  real defect can separate.
  -- The episode-segment check in ladder_breaks below is THAT SAME IDENTITY rearranged, so
  -- it is a second test of the one thing rather than a nineteenth test of a nineteenth
  -- thing. The event-segment check is a tautology: n_out(19) is written as the same
  -- expression as n_out(17) - n_dropped(18).
  --
  -- SO: EIGHTEEN OF THE NINETEEN closes_exact VALUES ARE TRUE BY CONSTRUCTION, and the
  -- closure column's whole empirical content is step 16. It is not small; it is exactly
  -- the failure that can happen here, an episode that is neither eligible nor charged to a
  -- rung, and the ladder does catch it. But NOTHING DOWNSTREAM MAY READ closes_exact AS
  -- NINETEEN INDEPENDENT CHECKS, and make_strobe.py must not re-derive confidence from
  -- the column being uniformly true. Left as computed rather than rebuilt on independent
  -- counts because steps 1, 2, 17, 18 and 19 have no second source that is not a second
  -- scan of a large CDR table, so a partial rebuild would still need this paragraph and
  -- would buy a false uniformity. DAG-SCHEMA 8.14 carries the same map.
  --
  -- reason is a SLUG, is NEVER NULL, and takes exactly the three values EXPORT-CONTRACT
  -- 3.3 fixes: the rung's own slug on an exclusion rung, the literal 'unit_change' on a
  -- conversion rung, and the empty string on a terminal rung. It is keyed off kind and
  -- not off the nullness of n_dropped, which is a different question: step 2 is a
  -- conversion that also drops and step 17 is a conversion that does not.
  -- The printable sentence is LABELS[slug] in 07_export.py, keyed by the RUNG SLUG and
  -- not by reason, because the label table of EXPORT-CONTRACT 7.2 has nineteen rung-slug
  -- keys and no 'unit_change' key. No display string is ever written by SQL, so a reason
  -- cannot be paraphrased at render time.
  --
  -- THE COUNTS HERE ARE TRUE INTEGERS AND ARE NOT ROUNDED. 07_export.py must pass every
  -- one through disclosure.round20 and disclosable() before it reaches any surface.
  --
  -- Grain: exactly 19 rows. junction_map records which map produced this ladder, because
  -- the primary and the mirrored run legitimately produce DIFFERENT ladders: under the
  -- mirrored map an episode whose only evidence is cervicothoracic moves from cervical
  -- to thoracic-only, that is from included to excluded at rung 8.
  -- ===================================================================================
  IF start_ix <= 15 THEN
  -- @stage-begin: attrition
  CREATE OR REPLACE TABLE `{DERIVED}.attrition` AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  ladder AS (
    SELECT * FROM UNNEST([
      STRUCT( 1 AS step, 'program_participants'                          AS slug, 'exclusion'  AS kind, 'persons'             AS unit),
      STRUCT( 2,         'episode_construction',                                  'conversion',        'persons to episodes'),
      STRUCT( 3,         'excl_trauma_malignancy_infection',                      'exclusion',         'episodes'),
      STRUCT( 4,         'excl_ed_encounter_not_elective',                        'exclusion',         'episodes'),
      STRUCT( 5,         'excl_prior_operation_90_days',                          'exclusion',         'episodes'),
      STRUCT( 6,         'excl_simultaneous_cervical_lumbar',                     'exclusion',         'episodes'),
      STRUCT( 7,         'excl_region_unspecified_only',                          'exclusion',         'episodes'),
      STRUCT( 8,         'excl_thoracic_only',                                    'exclusion',         'episodes'),
      STRUCT( 9,         'excl_add_on_code_only',                                 'exclusion',         'episodes'),
      STRUCT(10,         'excl_missing_discharge_date',                           'exclusion',         'episodes'),
      STRUCT(11,         'excl_no_wearable_data',                                 'exclusion',         'episodes'),
      STRUCT(12,         'excl_inadequate_baseline_wear',                         'exclusion',         'episodes'),
      STRUCT(13,         'excl_not_first_eligible_episode',                       'exclusion',         'episodes'),
      STRUCT(14,         'excl_no_computable_post_discharge_window',              'exclusion',         'episodes'),
      STRUCT(15,         'excl_window_truncated_by_death_or_reoperation',         'exclusion',         'episodes'),
      STRUCT(16,         'analytic_cohort',                                       'terminal',          'episodes'),
      STRUCT(17,         'events_identified',                                     'conversion',        'episodes to events'),
      STRUCT(18,         'excl_event_without_computable_landmark',                'exclusion',         'events'),
      STRUCT(19,         'events_analyzable',                                     'terminal',          'events')
    ])
  ),
  tot AS (
    SELECT
      (SELECT COUNT(*) FROM `{CDR}.person`) AS n_persons_total,
      (SELECT COUNT(DISTINCT o.person_id)
       FROM `{CDR}.procedure_occurrence` AS o
       JOIN `{DERIVED}.cs_spine` AS s ON s.concept_id = o.procedure_source_concept_id)
        AS n_persons_with_concept,
      (SELECT COUNT(DISTINCT person_id) FROM `{DERIVED}.episodes`) AS n_persons_with_episode,
      (SELECT COUNT(*) FROM `{DERIVED}.episodes`)                  AS n_episodes,
      (SELECT COUNT(*) FROM `{DERIVED}.episodes_eligible` WHERE is_eligible) AS n_analytic,
      (SELECT COUNT(*) FROM `{DERIVED}.events` WHERE is_first_event)         AS n_events_identified,
      (SELECT COUNTIF(structurally_uncomputable_landmark)
       FROM `{DERIVED}.events` WHERE is_first_event)                         AS n_events_uncomputable
  ),
  dd AS (
    SELECT first_fail_step AS step, COUNT(*) AS n_dropped
    FROM `{DERIVED}.episodes_eligible`
    WHERE first_fail_step IS NOT NULL
    GROUP BY step
  ),
  d AS (
    SELECT s AS step, IFNULL(dd.n_dropped, 0) AS n_dropped
    FROM UNNEST(GENERATE_ARRAY(3, 15)) AS s
    LEFT JOIN dd ON dd.step = s
  ),
  chain AS (
    SELECT
      d.step,
      d.n_dropped,
      (SELECT n_episodes FROM tot)
        - IFNULL(SUM(d.n_dropped) OVER (ORDER BY d.step ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)
        AS n_in
    FROM d
  ),
  counts AS (
    SELECT 1 AS step, n_persons_total AS n_in,
           n_persons_total - n_persons_with_concept AS n_dropped,
           n_persons_with_concept AS n_out,
           CAST(NULL AS INT64) AS n_carried_forward
    FROM tot
    UNION ALL
    SELECT 2, n_persons_with_concept,
           n_persons_with_concept - n_persons_with_episode,
           n_episodes,
           n_persons_with_episode
    FROM tot
    UNION ALL
    SELECT step, n_in, n_dropped, n_in - n_dropped, CAST(NULL AS INT64) FROM chain
    UNION ALL
    SELECT 16, n_analytic, CAST(NULL AS INT64), n_analytic, CAST(NULL AS INT64) FROM tot
    UNION ALL
    SELECT 17, n_analytic, CAST(NULL AS INT64), n_events_identified, CAST(NULL AS INT64) FROM tot
    UNION ALL
    SELECT 18, n_events_identified, n_events_uncomputable,
           n_events_identified - n_events_uncomputable, CAST(NULL AS INT64) FROM tot
    UNION ALL
    SELECT 19, n_events_identified - n_events_uncomputable, CAST(NULL AS INT64),
           n_events_identified - n_events_uncomputable, CAST(NULL AS INT64) FROM tot
  ),
  joined AS (
    SELECT
      l.step, l.slug, l.kind, l.unit,
      c.n_in, c.n_dropped, c.n_out, c.n_carried_forward,
      -- reason is keyed off kind, NOT off whether n_dropped happens to be null, because
      -- EXPORT-CONTRACT 3.3 fixes three cases and two of them are not "an exclusion that
      -- dropped rows": a conversion rung carries the literal 'unit_change' whether or not
      -- it also drops (step 2 does, step 17 does not), and a terminal rung carries the
      -- empty string, which is the not-applicable convention and never a suppression.
      -- Never null, so 07_export.py cannot be handed a null to key a lookup with.
      CASE WHEN l.kind = 'conversion' THEN 'unit_change'
           WHEN l.kind = 'terminal'   THEN ''
           ELSE l.slug END AS reason,
      LAG(c.n_out) OVER (ORDER BY l.step) AS prev_n_out
    FROM ladder AS l
    JOIN counts AS c USING (step)
  )
  SELECT
    j.step, j.slug, j.kind, j.unit,
    j.n_in, j.n_dropped, j.n_out, j.n_carried_forward, j.reason,
    (
      (j.step = 1 OR j.n_in = j.prev_n_out)
      AND CASE j.step
            WHEN 2  THEN j.n_in - j.n_dropped = j.n_carried_forward AND j.n_out >= j.n_carried_forward
            WHEN 16 THEN j.n_in = j.n_out AND j.n_dropped IS NULL
            WHEN 17 THEN j.n_dropped IS NULL AND j.n_out >= 0
            WHEN 19 THEN j.n_in = j.n_out AND j.n_dropped IS NULL
            ELSE j.n_in - j.n_dropped = j.n_out
          END
    ) AS closes_exact,
    p.junction_map,
    p.built_at
  FROM joined AS j
  CROSS JOIN p
  ORDER BY j.step;
  -- @stage-end: attrition

  -- THE LADDER IS A STOP CONDITION. If it does not close, raise. Do not adjust a count
  -- to make it close. Three checks: every rung's own identity, the episode segment, and
  -- the event segment. Steps 17 and 19 are excluded from the episode segment because
  -- they count events.
  --
  -- IS NOT TRUE rather than NOT, because COUNTIF(NOT x) does not count a null and a null
  -- closes_exact would therefore pass this stop condition in silence. No path produces
  -- one today; the clause is here so that none can.
  SET ladder_breaks = (
    SELECT
      COUNTIF(closes_exact IS NOT TRUE)
      + IF((SELECT SUM(n_dropped) FROM `{DERIVED}.attrition` WHERE step BETWEEN 3 AND 15)
           + (SELECT n_out FROM `{DERIVED}.attrition` WHERE step = 16)
           != (SELECT n_out FROM `{DERIVED}.attrition` WHERE step = 2), 1, 0)
      + IF((SELECT n_out FROM `{DERIVED}.attrition` WHERE step = 17)
           - (SELECT n_dropped FROM `{DERIVED}.attrition` WHERE step = 18)
           != (SELECT n_out FROM `{DERIVED}.attrition` WHERE step = 19), 1, 0)
    FROM `{DERIVED}.attrition`
  );
  IF ladder_breaks > 0 THEN
    RAISE USING MESSAGE = 'The attrition ladder does not close. Query {DERIVED}.attrition for the rungs where closes_exact is false, and check the episode segment (the sum of n_dropped over steps 3 to 15 plus the analytic n of step 16 must equal the n_out of step 2) and the event segment (n_out of step 17 minus n_dropped of step 18 must equal n_out of step 19). Do not adjust a count to make it close.';
  END IF;

  IF (SELECT COUNT(*) FROM `{DERIVED}.attrition`) != 19 THEN
    RAISE USING MESSAGE = 'The attrition ladder does not have exactly nineteen rungs. ANALYSIS-PLAN 2.6 owns the rung list and local/verify.py asserts set equality against it.';
  END IF;

  -- The six-row derivation of ANALYSIS-PLAN 4.3, checked rather than trusted: an event
  -- whose proximal window carries fewer than two post-discharge days is exactly an
  -- event on post-discharge day 1 to 4. If this fails, the date arithmetic in the
  -- events stage is wrong and rung 18 is counting the wrong events.
  IF (SELECT COUNTIF(structurally_uncomputable_landmark != (event_post_discharge_day <= 4))
      FROM `{DERIVED}.events`) > 0 THEN
    RAISE USING MESSAGE = 'The structurally uncomputable landmark flag does not agree with post-discharge day 1 to 4. ANALYSIS-PLAN 4.3 derives that range in six rows and rung 18 counts on it; a disagreement means the proximal window arithmetic is wrong.';
  END IF;
  END IF;

  -- ===================================================================================
  -- STAGE 16 of 19: ledger_exclusion_reasons
  -- STROBE companion ledger 3 of 5, the exclusion and censoring reason ledger. This is
  -- where the breakdowns that CANNOT be rungs go, because rows here may overlap and are
  -- explicitly NOT a partition: an episode excluded at rung 3 may carry trauma AND
  -- malignancy, and it is counted under both.
  --
  -- n_denominator is the honest denominator for the share the exporter prints, and it
  -- is not always the rung's n_dropped: for the rung 4 rescue routes the population at
  -- risk of being rescued is the set of episodes with an emergency department encounter,
  -- not the set that failed the rung. 07_export.py computes
  -- share_of_step_dropped = n_episodes / n_denominator and applies the disclosure floor
  -- to both before either is printed.
  --
  -- Grain: one row per reason detail within a rung. Roughly 20 rows. Counts are TRUE
  -- INTEGERS and must be rounded and floor-tested before export.
  -- ===================================================================================
  IF start_ix <= 16 THEN
  -- @stage-begin: ledger_exclusion_reasons
  CREATE OR REPLACE TABLE `{DERIVED}.ledger_exclusion_reasons` AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  -- The baseline table is joined in because rung 12's breakdown needs the two
  -- components of the rule, the valid-day count and the span, which episodes_eligible
  -- reduces to a single boolean.
  x AS (
    SELECT ee.*, b.n_valid_baseline_days, b.baseline_span_days, b.baseline_steps
    FROM `{DERIVED}.episodes_eligible` AS ee
    JOIN `{DERIVED}.baseline` AS b USING (episode_id)
  ),
  denom AS (
    SELECT
      COUNTIF(first_fail_step = 3)  AS n_step3,
      COUNTIF(first_fail_step = 4)  AS n_step4,
      COUNTIF(first_fail_step = 12) AS n_step12,
      COUNTIF(first_fail_step = 14) AS n_step14,
      COUNTIF(first_fail_step = 15) AS n_step15,
      COUNTIF(ed_encounter_present) AS n_ed_present,
      COUNTIF(is_eligible)          AS n_analytic
    FROM x
  ),
  rows_out AS (
    -- Rung 3, the composite nonelective-indication screen, broken out by indication.
    SELECT 3 AS step, 'excl_trauma_malignancy_infection' AS slug, 'trauma' AS reason_detail,
           (SELECT COUNTIF(first_fail_step = 3 AND ind_trauma) FROM x) AS n_episodes,
           (SELECT n_step3 FROM denom) AS n_denominator
    UNION ALL SELECT 3, 'excl_trauma_malignancy_infection', 'spinal_cord_injury',
           (SELECT COUNTIF(first_fail_step = 3 AND ind_spinal_cord_injury) FROM x), (SELECT n_step3 FROM denom)
    UNION ALL SELECT 3, 'excl_trauma_malignancy_infection', 'malignancy',
           (SELECT COUNTIF(first_fail_step = 3 AND ind_malignancy) FROM x), (SELECT n_step3 FROM denom)
    UNION ALL SELECT 3, 'excl_trauma_malignancy_infection', 'metastatic_disease',
           (SELECT COUNTIF(first_fail_step = 3 AND ind_metastatic_disease) FROM x), (SELECT n_step3 FROM denom)
    UNION ALL SELECT 3, 'excl_trauma_malignancy_infection', 'spinal_infection',
           (SELECT COUNTIF(first_fail_step = 3 AND ind_spinal_infection) FROM x), (SELECT n_step3 FROM denom)

    -- Rung 4, the elective proxy: the three rescue routes, over the episodes at risk of
    -- being rescued rather than over the episodes that were dropped.
    UNION ALL SELECT 4, 'excl_ed_encounter_not_elective', 'ed_encounter_present',
           (SELECT n_ed_present FROM denom), (SELECT n_ed_present FROM denom)
    UNION ALL SELECT 4, 'excl_ed_encounter_not_elective', 'rescue_elective_coded',
           (SELECT COUNTIF(ed_encounter_present AND rescue_elective_coded) FROM x), (SELECT n_ed_present FROM denom)
    UNION ALL SELECT 4, 'excl_ed_encounter_not_elective', 'rescue_degenerative_index',
           (SELECT COUNTIF(ed_encounter_present AND rescue_degenerative_index) FROM x), (SELECT n_ed_present FROM denom)
    UNION ALL SELECT 4, 'excl_ed_encounter_not_elective', 'rescue_degenerative_outpatient_90d',
           (SELECT COUNTIF(ed_encounter_present AND rescue_degenerative_outpatient_90d) FROM x), (SELECT n_ed_present FROM denom)

    -- Rung 12, which of the two baseline conditions bound.
    UNION ALL SELECT 12, 'excl_inadequate_baseline_wear', 'no_valid_baseline_day',
           (SELECT COUNTIF(first_fail_step = 12 AND n_valid_baseline_days = 0) FROM x),
           (SELECT n_step12 FROM denom)
    UNION ALL SELECT 12, 'excl_inadequate_baseline_wear', 'fewer_than_seven_valid_days',
           (SELECT COUNTIF(first_fail_step = 12 AND n_valid_baseline_days BETWEEN 1 AND 6) FROM x),
           (SELECT n_step12 FROM denom)
    UNION ALL SELECT 12, 'excl_inadequate_baseline_wear', 'baseline_span_under_14_days',
           (SELECT COUNTIF(first_fail_step = 12 AND n_valid_baseline_days >= 7 AND baseline_span_days < 14) FROM x),
           (SELECT n_step12 FROM denom)

    -- Rung 14, whether the window was empty of analyzable days or empty of at-risk days.
    UNION ALL SELECT 14, 'excl_no_computable_post_discharge_window', 'no_analyzable_day_in_window',
           (SELECT COUNTIF(first_fail_step = 14 AND n_analyzable_days_1_35 = 0) FROM x), (SELECT n_step14 FROM denom)
    UNION ALL SELECT 14, 'excl_no_computable_post_discharge_window', 'not_at_risk_in_window',
           (SELECT COUNTIF(first_fail_step = 14 AND n_at_risk_days_1_35 = 0) FROM x), (SELECT n_step14 FROM denom)

    -- Rung 15, which truncation removed the episode.
    UNION ALL SELECT 15, 'excl_window_truncated_by_death_or_reoperation', 'death',
           (SELECT COUNTIF(first_fail_step = 15 AND censor_reason = 'death') FROM x), (SELECT n_step15 FROM denom)
    UNION ALL SELECT 15, 'excl_window_truncated_by_death_or_reoperation', 'repeat_spine_operation',
           (SELECT COUNTIF(first_fail_step = 15 AND censor_reason = 'repeat_spine_operation') FROM x), (SELECT n_step15 FROM denom)

    -- The censoring reasons of 2.3, over the ANALYTIC cohort. A censored day is not a
    -- missing day: the episode is not at risk on it and the window is shortened.
    UNION ALL SELECT 16, 'analytic_cohort', 'censoring_none',
           (SELECT COUNTIF(is_eligible AND censor_reason = 'none') FROM x), (SELECT n_analytic FROM denom)
    UNION ALL SELECT 16, 'analytic_cohort', 'censoring_death',
           (SELECT COUNTIF(is_eligible AND censor_reason = 'death') FROM x), (SELECT n_analytic FROM denom)
    UNION ALL SELECT 16, 'analytic_cohort', 'censoring_repeat_spine_operation',
           (SELECT COUNTIF(is_eligible AND censor_reason = 'repeat_spine_operation') FROM x), (SELECT n_analytic FROM denom)
    UNION ALL SELECT 16, 'analytic_cohort', 'censoring_cdr_observation_cutoff',
           (SELECT COUNTIF(is_eligible AND censor_reason = 'cdr_observation_cutoff') FROM x), (SELECT n_analytic FROM denom)
  )
  SELECT r.*, p.junction_map
  FROM rows_out AS r
  CROSS JOIN p
  ORDER BY r.step, r.reason_detail;
  -- @stage-end: ledger_exclusion_reasons

  -- Every slug in this ledger must be a member of the nineteen-rung vocabulary. A slug
  -- here that is not a rung slug is a failure, per EXPORT-CONTRACT.md section 5.6.
  IF (SELECT COUNT(*)
      FROM `{DERIVED}.ledger_exclusion_reasons` AS l
      LEFT JOIN `{DERIVED}.attrition` AS a ON a.slug = l.slug AND a.step = l.step
      WHERE a.slug IS NULL) > 0 THEN
    RAISE USING MESSAGE = 'The exclusion-reason ledger carries a step and slug pair that is not a rung of the nineteen-rung ladder.';
  END IF;
  END IF;

  -- ===================================================================================
  -- STAGE 17 of 19: ledger_wear_by_day
  -- STROBE companion ledger 4 of 5. One row per procedure group per post-discharge day
  -- 1 to 90. All SEVEN group slugs of ANALYSIS-PLAN 2.4 are emitted, because the group
  -- set that survives is decided by the collapse level of 2.5, which is decided on the
  -- attrition ladder AFTER this table exists. No consumer may hardcode four groups.
  --
  -- group_order carries the plan's print order with the two collapse-level-2 groups
  -- appended as 6 and 7, since the plan writes them as 2a and 2b and this is an integer
  -- column. 07_export.py owns the plan's order vocabulary and may relabel.
  --
  -- THE ABSENCE RULE OF FIGURE 2 IS AN EXPORT-TIME RULE, NOT A BUILD-TIME ONE. A day
  -- whose n_at_risk fails the disclosure floor is dropped from the FILE by 07_export.py
  -- rather than written as a suppressed row, because a list of which days were hidden
  -- recovers the pattern it was hiding. This table carries every day.
  --
  -- Grain: one row per group per post-discharge day. Up to 7 by 90, so 630 rows.
  -- ===================================================================================
  IF start_ix <= 17 THEN
  -- @stage-begin: ledger_wear_by_day
  CREATE OR REPLACE TABLE `{DERIVED}.ledger_wear_by_day` AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  memb AS (
    SELECT episode_id, procedure_group AS group_slug,
           CASE procedure_group
             WHEN 'cervical_decompression' THEN 1
             WHEN 'cervical_fusion'        THEN 2
             WHEN 'lumbar_decompression'   THEN 3
             WHEN 'lumbar_fusion'          THEN 4
           END AS group_order
    FROM `{DERIVED}.features`
    WHERE procedure_group IS NOT NULL
    UNION ALL
    SELECT episode_id, 'all_groups', 5 FROM `{DERIVED}.features`
    UNION ALL
    SELECT episode_id, procedure_class, IF(procedure_class = 'fusion', 6, 7)
    FROM `{DERIVED}.features`
  )
  SELECT
    m.group_slug,
    m.group_order,
    dd.post_discharge_day AS day,
    COUNTIF(NOT dd.is_censored)  AS n_at_risk,
    COUNTIF(dd.valid_wear AND NOT dd.is_censored)   AS n_valid_wear,
    COUNTIF(dd.is_analyzable)                       AS n_analyzable,
    COUNTIF(dd.is_inpatient AND NOT dd.is_censored) AS n_inpatient,
    p.junction_map
  FROM `{DERIVED}.drd_daily` AS dd
  JOIN memb AS m USING (episode_id)
  CROSS JOIN p
  GROUP BY m.group_slug, m.group_order, dd.post_discharge_day, p.junction_map
  ORDER BY m.group_order, day;
  -- @stage-end: ledger_wear_by_day
  END IF;

  -- ===================================================================================
  -- STAGE 18 of 19: ledger_matched_sets
  -- STROBE companion ledger 5 of 5. The distribution of controls per case from the
  -- risk-set sampling of 4.5, which is the number that shows whether the two caps bit
  -- and how hard. This table is EMPTY when Arm A produced no sets. It is deliberately
  -- still created, because a file that is present and empty and a file that is absent
  -- are different claims and only one of them is checkable; 07_export.py writes the
  -- one-row "no Arm A analysis at this tier" statement when it reads zero rows here.
  --
  -- Grain: one row per distinct set size. A handful of rows.
  -- ===================================================================================
  IF start_ix <= 18 THEN
  -- @stage-begin: ledger_matched_sets
  CREATE OR REPLACE TABLE `{DERIVED}.ledger_matched_sets` AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  per_set AS (
    SELECT set_id, ANY_VALUE(set_size) AS set_size, ANY_VALUE(case_episode_id) AS case_episode_id
    FROM `{DERIVED}.risk_sets`
    GROUP BY set_id
  )
  SELECT
    per_set.set_size,
    COUNT(*)                             AS n_sets,
    COUNT(DISTINCT per_set.case_episode_id) AS n_cases,
    p.junction_map
  FROM per_set
  CROSS JOIN p
  GROUP BY per_set.set_size, p.junction_map
  ORDER BY per_set.set_size;
  -- @stage-end: ledger_matched_sets
  END IF;

  -- ===================================================================================
  -- STAGE 19 of 19: ledger_variable_missingness
  -- The count half of STROBE companion ledger 2 of 5, variable provenance. Every other
  -- column of that ledger (display label, role, source table, derivation, unit, missing
  -- handling) is a SPECIFICATION fact and is owned by 07_export.py, which is also where
  -- the display strings live. Only n_missing is a fact about the data, so only
  -- n_missing is computed here.
  --
  -- A ROW HERE MUST COUNT THE EVIDENCE OF ABSENCE, NEVER THE SUBSTITUTED VALUE. Where
  -- features substitutes, it also carries the flag that records the substitution, and the
  -- row counts the flag: bmi counts bmi_missing rather than bmi_imputed IS NULL, and
  -- charlson_score counts charlson_missing rather than charlson_score IS NULL, which is
  -- unsatisfiable because the IFNULL scoring rule makes that column non-null by
  -- construction. sex_at_birth and device_family count their own 'other_or_unknown'
  -- level, which IS the evidence rather than a substitution over it.
  -- Three rows are expected to be structurally zero, and only these three: los_days,
  -- baseline_steps and procedure_group, because an upstream rung has already removed every
  -- episode that could have been missing them. A zero there is a true statement about the
  -- cohort. A zero produced by a substitution is not, and is the defect this paragraph
  -- exists to keep from coming back.
  --
  -- Grain: one row per analysis variable. Around a dozen rows.
  -- ===================================================================================
  IF start_ix <= 19 THEN
  -- @stage-begin: ledger_variable_missingness
  CREATE OR REPLACE TABLE `{DERIVED}.ledger_variable_missingness` AS
  WITH p AS (SELECT * FROM `{DERIVED}.build_params`),
  f AS (SELECT * FROM `{DERIVED}.features`),
  n AS (SELECT COUNT(*) AS n_total FROM f),
  rows_out AS (
    SELECT 'age_at_index' AS variable, (SELECT n_total FROM n) AS n_total,
           (SELECT COUNTIF(age_at_index IS NULL) FROM f) AS n_missing
    UNION ALL SELECT 'sex_at_birth', (SELECT n_total FROM n),
           (SELECT COUNTIF(sex_at_birth = 'other_or_unknown') FROM f)
    UNION ALL SELECT 'race_concept_id', (SELECT n_total FROM n),
           (SELECT COUNTIF(race_concept_id IS NULL OR race_concept_id = 0) FROM f)
    UNION ALL SELECT 'ethnicity_concept_id', (SELECT n_total FROM n),
           (SELECT COUNTIF(ethnicity_concept_id IS NULL OR ethnicity_concept_id = 0) FROM f)
    UNION ALL SELECT 'bmi', (SELECT n_total FROM n), (SELECT COUNTIF(bmi_missing) FROM f)
    UNION ALL SELECT 'charlson_score', (SELECT n_total FROM n),
           (SELECT COUNTIF(charlson_missing) FROM f)
    UNION ALL SELECT 'los_days', (SELECT n_total FROM n), (SELECT COUNTIF(los_days IS NULL) FROM f)
    UNION ALL SELECT 'device_family', (SELECT n_total FROM n),
           (SELECT COUNTIF(device_family = 'other_or_unknown') FROM f)
    UNION ALL SELECT 'baseline_steps', (SELECT n_total FROM n),
           (SELECT COUNTIF(baseline_steps IS NULL) FROM f)
    UNION ALL SELECT 'procedure_group', (SELECT n_total FROM n),
           (SELECT COUNTIF(procedure_group IS NULL) FROM f)
    UNION ALL SELECT 'daily_deficit', (SELECT COUNT(*) FROM `{DERIVED}.drd_daily` WHERE in_accrual_window),
           (SELECT COUNTIF(deficit IS NULL) FROM `{DERIVED}.drd_daily` WHERE in_accrual_window)
    UNION ALL SELECT 'r72', (SELECT COUNT(*) FROM `{DERIVED}.events` WHERE is_first_event),
           (SELECT COUNTIF(r72 IS NULL) FROM `{DERIVED}.events` WHERE is_first_event)
  )
  SELECT r.*, p.junction_map
  FROM rows_out AS r
  CROSS JOIN p
  ORDER BY r.variable;
  -- @stage-end: ledger_variable_missingness
  END IF;

END;


-- =====================================================================================
-- WHAT A RESUMED SESSION RUNS
--
--   %run 00_config.ipynb          resolves {CDR}, {PREP}, {DERIVED} and the location
--   python3 03_cohort.py --call   dry-runs every stage, prints the bytes, then CALLs
--
-- Nothing above needs the previous session's compute disk, its /tmp, or any parquet.
-- The tables are in the CDR's own project and outlive the environment, which is the
-- whole reason this file is a stored procedure.
--
-- To rebuild only part of the DAG, pass start_stage. To run the mirrored-junction
-- sensitivity, pass junction_map = 'mirrored', which produces a DIFFERENT and equally
-- correct ladder; nothing compares one run's rung counts to the other's.
-- =====================================================================================
