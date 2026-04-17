# Joboro Database: Complete Table Reference Guide

This document provides a comprehensive reference of all database tables in the Joboro platform, organized by functional area with clear descriptions of their purpose and relationships.

---

## 1. CORE USER MANAGEMENT TABLES

### `auth_user`
**Purpose:** Standard Django authentication system user table
**Key Fields:** id, username, password, email, is_staff, is_active, last_login, date_joined
**Relationships:** Related to auth_group, auth_permission via junction tables
**Use When:** Managing system authentication, user permissions, login credentials

### `core_users_candidates`
**Purpose:** Stores detailed candidate profile information
**Key Fields:** id, fname, lname, email, primary_contact, country, dob, gender, work_status, entity_id
**Relationships:** 
- `entity_id` → `core_entities.id`
- One-to-one with `candidate_details`, `candidate_cv_data`
- One-to-many with `vacancy_applicants`, `candidate_experiences`, `candidate_qualifications`
**Use When:** Querying candidate profiles, searching candidates, candidate analytics

### `core_users_recruiters`
**Purpose:** Stores recruiter profile information
**Key Fields:** id, fname, lname, email, company_id, role, is_status, entity_id
**Relationships:**
- `company_id` → `core_companies.id`
- `entity_id` → `core_entities.id`
- One-to-many with `interviews` (as interviewer)
**Use When:** Managing recruiters, assigning interviewers, recruiter performance tracking

### `core_users_internal`
**Purpose:** System administrators and internal staff users
**Key Fields:** id, fname, lname, email, role, entity_id
**Relationships:** `entity_id` → `core_entities.id`
**Use When:** System administration, internal user management

### `core_users_recruiter_roles`
**Purpose:** Defines roles and permission groups for recruiters
**Key Fields:** id, name, description, company_id
**Relationships:** `company_id` → `core_companies.id`
**Use When:** Role-based access control, recruiter permission management

### `core_users_recruiter_role_permissions`
**Purpose:** Junction table linking roles to specific permissions
**Key Fields:** id, role_id, permission_id
**Relationships:**
- `role_id` → `core_users_recruiter_roles.id`
- `permission_id` → `core_permissions.id`
**Use When:** Assigning permissions to recruiter roles

### `core_users_recruiter_invitations`
**Purpose:** Tracks invitations sent to potential recruiters
**Key Fields:** id, name, email, role_id, company_id, uuid
**Relationships:**
- `role_id` → `core_users_recruiter_roles.id`
- `company_id` → `core_companies.id`
**Use When:** Managing recruiter onboarding, tracking invitations

### `email_verify`
**Purpose:** Email verification token management
**Key Fields:** id, candidate_id, recruiter_id, token, expiry_date
**Use When:** Email verification flows, password reset processes

### `user_otps`
**Purpose:** One-time passwords for authentication
**Key Fields:** id, email, otp, expiry_time
**Use When:** Two-factor authentication, phone verification

---

## 2. ENTITY & ORGANIZATION TABLES

### `core_entities`
**Purpose:** Central polymorphic entity hub for ownership tracking
**Key Fields:** id, type, created_by_id, updated_by_id
**Relationships:**
- `created_by_id` → `core_users_internal.id`
- `updated_by_id` → `core_users_internal.id`
- Referenced by nearly all business tables
**Use When:** Tracking ownership, polymorphic relationships, audit trails

### `core_companies`
**Purpose:** Main company/organization information
**Key Fields:** id, name, email, logo, website, country, size, founded, status, subscription_id
**Relationships:**
- `entity_id` → `core_entities.id`
- One-to-many with `vacancies`, `core_users_recruiters`, `interview_configs`
**Use When:** Company management, subscription management, company analytics

### `core_domains`
**Purpose:** Industry sectors and domains
**Key Fields:** id, title, description, icon, entity_id
**Relationships:** `entity_id` → `core_entities.id`
**Use When:** Categorizing jobs by industry, candidate domain preferences

### `core_job_titles`
**Purpose:** Standardized job titles
**Key Fields:** id, title, description, domain_id, entity_id
**Relationships:**
- `domain_id` → `core_domains.id`
- `entity_id` → `core_entities.id`
**Use When:** Job title standardization, vacancy creation, candidate job preferences

### `core_skills`
**Purpose:** Standardized skill definitions
**Key Fields:** id, title, description, domain_id, entity_id, company_id
**Relationships:**
- `domain_id` → `core_domains.id`
- `entity_id` → `core_entities.id`
**Use When:** Skill management, vacancy requirements, candidate skill assessment

### `core_skill_topics`
**Purpose:** Specific topics within skills for interview questions
**Key Fields:** id, skill_id, topic, difficulty, topic_type, expected_content
**Relationships:** `skill_id` → `core_skills.id`
**Use When:** Generating interview questions, skill-specific assessments

### `core_countries`
**Purpose:** Country reference data
**Key Fields:** id, country, code, default_currency
**Use When:** Geographic filtering, location-based analytics

### `core_currencies`
**Purpose:** Currency reference with USD conversion rates
**Key Fields:** id, currency, rate_in_usd, date
**Use When:** Salary calculations, financial reporting

---

## 3. VACANCY & APPLICATION TABLES

### `vacancies`
**Purpose:** Job openings and position details
**Key Fields:** id, title, jd, description, company_id, domain_id, job_title_id, status, expiry_date, work_mode, salary_scale
**Relationships:**
- `company_id` → `core_companies.id`
- `domain_id` → `core_domains.id`
- `job_title_id` → `core_job_titles.id`
- `entity_id` → `core_entities.id`
**Use When:** Creating/managing jobs, vacancy listings, job search

### `vacancy_skills`
**Purpose:** Skills required for each vacancy
**Key Fields:** id, vacancy_id, skill_id, expert_level
**Relationships:**
- `vacancy_id` → `vacancies.id`
- `skill_id` → `core_skills.id`
**Use When:** Skill matching, vacancy requirements analysis

### `vacancy_screening_steps`
**Purpose:** Recruitment process stages for vacancies
**Key Fields:** id, vacancy_id, step_name, step_type, order_index, is_published, mark_percentages, duration
**Relationships:**
- `vacancy_id` → `vacancies.id`
- `company_id` → `core_companies.id`
- `added_by_id` → `core_users_recruiters.id`
**Use When:** Defining recruitment workflow, stage management, candidate progression

### `vacancy_applicants`
**Purpose:** Candidate applications to vacancies
**Key Fields:** id, vacancy_id, candidate_id, applied_date, status, current_step_id, ai_score, apply_via, is_rejected
**Relationships:**
- `vacancy_id` → `vacancies.id`
- `candidate_id` → `core_users_candidates.id`
- `entity_id` → `core_entities.id`
- `current_step_id` → `vacancy_screening_steps.id`
**Use When:** Application tracking, candidate screening, application analytics

### `vacancy_applicant_steps`
**Purpose:** Tracks candidate progress through screening steps
**Key Fields:** id, applicant_id, step_id, status, completed_on, total_actual_score, is_pass
**Relationships:**
- `applicant_id` → `vacancy_applicants.id`
- `step_id` → `vacancy_screening_steps.id`
**Use When:** Step-by-step progress tracking, scoring, completion status

### `vacancy_applicant_step_results`
**Purpose:** Individual question results for screening steps
**Key Fields:** id, vacancy_applicant_step_id, questionnaire_question_id, answer, marks, score_explanation
**Relationships:**
- `vacancy_applicant_step_id` → `vacancy_applicant_steps.id`
- `questionnaire_question_id` → `questionnaire_questions.id`
**Use When:** Detailed answer evaluation, scoring breakdown

### `questionnaires`
**Purpose:** Groups of questions for screening steps
**Key Fields:** id, title, description, vacancy_id, company_id, type
**Relationships:**
- `vacancy_id` → `vacancies.id`
- `company_id` → `core_companies.id`
**Use When:** Creating assessment forms, screening questionnaires

### `questionnaire_questions`
**Purpose:** Individual questions in questionnaires
**Key Fields:** id, questionnaire_id, question, field_type, order_index, is_required
**Relationships:** `questionnaire_id` → `questionnaires.id`
**Use When:** Question management, form building

### `questionnaire_question_options`
**Purpose:** Options for multiple-choice questions
**Key Fields:** id, questionnaire_question_id, option_value
**Relationships:** `questionnaire_question_id` → `questionnaire_questions.id` ON DELETE CASCADE
**Use When:** Dropdown, radio, checkbox question options

### `vss_ques_answer_expectations`
**Purpose:** Expected answers and evaluation criteria
**Key Fields:** id, questionnaire_question_id, expectation, marks, is_required
**Relationships:** `questionnaire_question_id` → `questionnaire_questions.id`
**Use When:** AI evaluation, answer grading, scoring criteria

---

## 4. INTERVIEW SYSTEM TABLES

### `interview_configs`
**Purpose:** Interview configuration templates
**Key Fields:** id, title, company_id, vacancy_id, avenues, agent_id
**Relationships:**
- `company_id` → `core_companies.id`
- `vacancy_id` → `vacancies.id`
**Use When:** Setting up interviews, configuring interview structure

### `interview_config_skills`
**Purpose:** Skills to test in interviews with parameters
**Key Fields:** id, config_id, skill_id, expert_level, number_of_questions, weightage
**Relationships:**
- `config_id` → `interview_configs.id`
- `skill_id` → `core_skills.id`
**Use When:** Skill-based interview configuration, weighting skills

### `interview_config_skill_topics`
**Purpose:** Specific topics per skill in interview config
**Key Fields:** id, config_id, topic, type, expected_content, ai_explaination
**Relationships:** `config_id` → `interview_configs.id`
**Use When:** Topic-specific questions, detailed interview content

### `interview_schedules`
**Purpose:** Scheduled interview appointments
**Key Fields:** id, candidate_id, vacancy_id, config_id, scheduled_date, status, type
**Relationships:**
- `candidate_id` → `core_users_candidates.id`
- `vacancy_id` → `vacancies.id`
- `applicant_id` → `vacancy_applicants.id`
- `config_id` → `interview_configs.id`
**Use When:** Interview scheduling, calendar management

### `interviews`
**Purpose:** Actual interview instances
**Key Fields:** id, code, schedule_id, candidate_id, start_time, end_time, interview_status, shortlist_status, score_domain_avg
**Relationships:**
- `schedule_id` → `interview_schedules.id`
- `candidate_id` → `core_users_candidates.id`
- `applicant_id` → `vacancy_applicants.id`
- `config_id` → `interview_configs.id`
**Use When:** Interview execution, result tracking, scoring

### `interview_results`
**Purpose:** Individual question results per interview
**Key Fields:** id, interview_id, question, skill_id, answer, score_domain, score_language, score_body_language
**Relationships:**
- `interview_id` → `interviews.id`
- `candidate_id` → `core_users_candidates.id`
**Use When:** Detailed question analysis, performance scoring

### `interview_feedbacks`
**Purpose:** Interviewer feedback on candidates
**Key Fields:** id, interview_id, overall_rating, criteria_rating, comments
**Relationships:** `interview_id` → `interviews.id`
**Use When:** Recruiter evaluation, feedback collection

### `interview_details`
**Purpose:** Additional interview metadata and analysis
**Key Fields:** id, interview_id, conversation, unwanted_actions, body_lang_score_json
**Relationships:** `interview_id` → `interviews.id`
**Use When:** Conversation analysis, behavioral insights

### `interview_question_score_json`
**Purpose:** Detailed scoring breakdown per question
**Key Fields:** id, interview_id, score_json
**Relationships:** `interview_id` → `interviews.id`
**Use When:** JSON-based scoring, detailed evaluation analysis

### `interview_reported_issues`
**Purpose:** Issues reported during interviews
**Key Fields:** id, interview_id, issue, screen_shot
**Relationships:** `interview_id` → `interviews.id`
**Use When:** Quality assurance, technical issue tracking

### `interview_bulk_schedules`
**Purpose:** Batch scheduling of multiple interviews
**Key Fields:** id, company_id, title, config_id, closing_date, status
**Relationships:**
- `company_id` → `core_companies.id`
- `config_id` → `interview_configs.id`
**Use When:** Mass interview invitations, bulk operations

---

## 5. CANDIDATE DATA TABLES

### `candidate_details`
**Purpose:** Extended candidate information
**Key Fields:** id, candidate_id, bio, cv_url, linkedin_url
**Relationships:** `candidate_id` → `core_users_candidates.id` (UNIQUE)
**Use When:** Rich candidate profiles, CV management

### `candidate_cv_data`
**Purpose:** Parsed CV data in JSON format
**Key Fields:** id, candidate_id, cv_data_json
**Relationships:** `candidate_id` → `core_users_candidates.id` (UNIQUE)
**Use When:** CV parsing, skill extraction, resume analysis

### `candidate_experiences`
**Purpose:** Work experience entries
**Key Fields:** id, candidate_id, title, company_id, company_name, year_from, year_to, is_working
**Relationships:**
- `candidate_id` → `core_users_candidates.id`
- `company_id` → `core_companies.id`
**Use When:** Experience tracking, career history, tenure analysis

### `candidate_qualifications`
**Purpose:** Educational qualifications
**Key Fields:** id, candidate_id, level, title, institute, year_from, year_to, is_studying
**Relationships:** `candidate_id` → `core_users_candidates.id`
**Use When:** Education verification, qualification analysis

### `candidate_skill_scores`
**Purpose:** Skill proficiency scores for candidates
**Key Fields:** id, candidate_id, skill_id, expertise, score, num_of_interviews
**Relationships:**
- `candidate_id` → `core_users_candidates.id`
- `skill_id` → `core_skills.id`
**Use When:** Skill assessment, candidate ranking, matching

### `candidate_skill_score_histories`
**Purpose:** Historical skill score tracking
**Key Fields:** id, candidate_id, skill_id, score, expertise
**Relationships:**
- `candidate_id` → `core_users_candidates.id`
- `skill_id` → `core_skills.id`
**Use When:** Skill progression analysis, improvement tracking

### `candidate_preference_commons`
**Purpose:** Candidate job preferences
**Key Fields:** id, candidate_id, preferred_countries, preferred_workmode, preferred_salary_in_usd, availability
**Relationships:** `candidate_id` → `core_users_candidates.id`
**Use When:** Candidate matching, job recommendations

### `candidate_preference_domains`
**Purpose:** Domain preferences (junction table)
**Key Fields:** id, candidate_id, domain_id
**Relationships:**
- `candidate_id` → `core_users_candidates.id`
- `domain_id` → `core_domains.id`
**Use When:** Industry preference tracking

### `candidate_preference_jobs`
**Purpose:** Job title preferences
**Key Fields:** id, candidate_id, job_title_id, skills
**Relationships:**
- `candidate_id` → `core_users_candidates.id`
- `job_title_id` → `core_job_titles.id`
**Use When:** Role preference analysis

### `candidate_experience_summary`
**Purpose:** Aggregated experience summary
**Key Fields:** id, candidate_id, experience_summary (JSON), counts (JSON)
**Relationships:** `candidate_id` → `core_users_candidates.id`
**Use When:** Quick experience overview, analytics

### `candidate_education_summary`
**Purpose:** Aggregated education summary
**Key Fields:** id, candidate_id, education_summary (JSON), counts (JSON)
**Relationships:** `candidate_id` → `core_users_candidates.id`
**Use When:** Education overview, qualification analytics

### `candidate_vacancy_bookmarks`
**Purpose:** Saved/bookmarked vacancies
**Key Fields:** id, candidate_id, vacancy_id, is_removed
**Relationships:**
- `candidate_id` → `core_users_candidates.id`
- `vacancy_id` → `vacancies.id`
**Use When:** Candidate saved jobs, interest tracking

### `candidate_company_bookmarks`
**Purpose:** Saved/bookmarked companies
**Key Fields:** id, candidate_id, company_id, is_removed
**Relationships:**
- `candidate_id` → `core_users_candidates.id`
- `company_id` → `core_companies.id`
**Use When:** Followed companies, employer interest

### `candidate_public_links`
**Purpose:** Public profile links (GitHub, portfolio, etc.)
**Key Fields:** id, candidate_id, url_options, link
**Relationships:** `candidate_id` → `core_users_candidates.id`
**Use When:** Portfolio links, social profiles

---

## 6. AI & LLM TABLES

### `ai_expectation`
**Purpose:** AI-generated answer expectations
**Key Fields:** id, question, expectation, type, job_description
**Use When:** Question generation, answer validation

### `ai_explanation`
**Purpose:** AI-generated explanations
**Key Fields:** id, question, explanation, job_description
**Use When:** Answer feedback, learning content

### `llm_api_project`
**Purpose:** LLM project configurations
**Key Fields:** id, name, system_prompt, llm_id, model_id
**Relationships:**
- `llm_id` → `llm_api_llm.id`
- `model_id` → `llm_api_model.id`
**Use When:** LLM configuration, prompt management

### `llm_api_llm`
**Purpose:** LLM provider configurations
**Key Fields:** id, name, base_url, api_key, auth_type
**Use When:** LLM provider setup, API management

### `llm_api_model`
**Purpose:** Model parameters for LLMs
**Key Fields:** id, model_id, parameters
**Use When:** Model configuration, parameter tuning

### `llm_api_newconversation`
**Purpose:** AI conversation logs
**Key Fields:** id, candidate_id, interview_id, message_type, message_content, sufficiency_score, termination_reason
**Use When:** Conversation analysis, AI behavior tracking

### `llm_api_formquestionevaluation`
**Purpose:** AI evaluation of question answers
**Key Fields:** id, interview_id, question, user_answer, expectation, score, score_explanation
**Use When:** Automated scoring, answer evaluation

### `initial_questions`
**Purpose:** Generated interview questions
**Key Fields:** id, candidate_id, interview_id, job_position, questions (JSON)
**Use When:** Question generation, interview setup

### `search_history`
**Purpose:** Search query tracking
**Key Fields:** id, user_input, response_format, ai_response (JSON)
**Use When:** Search analytics, query optimization

---

## 7. SUBSCRIPTION & PAYMENT TABLES

### `core_packages`
**Purpose:** Subscription packages
**Key Fields:** id, name, type, monthly_amount, yearly_amount, included_num_users
**Relationships:** `entity_id` → `core_entities.id`
**Use When:** Pricing plans, subscription management

### `core_subscriptions`
**Purpose:** Company subscriptions
**Key Fields:** id, company_id, package_id, from_date, to_date, is_closed, type
**Relationships:**
- `company_id` → `core_companies.id`
- `package_id` → `core_packages.id`
**Use When:** Subscription tracking, billing cycles

### `core_subscription_items`
**Purpose:** Active subscription periods
**Key Fields:** id, subscription_id, company_id, from_date, to_date, points, used_points, total_users
**Relationships:**
- `subscription_id` → `core_subscriptions.id`
- `company_id` → `core_companies.id`
**Use When:** Usage tracking, quota management

### `core_payments`
**Purpose:** Payment transactions
**Key Fields:** id, company_id, subscription_id, total_amount, type, invoice_num
**Relationships:** `company_id` → `core_companies.id`
**Use When:** Billing history, revenue analysis

### `subscription_payment_logs`
**Purpose:** Payment processing logs
**Key Fields:** id, company_id, status, payload (JSON), order_id
**Relationships:** `company_id` → `core_companies.id`
**Use When:** Payment debugging, transaction monitoring

### `core_coupons`
**Purpose:** Discount coupons
**Key Fields:** id, name, code, discount_percentage, months, expiry_date
**Use When:** Promotions, discounts

### `core_company_coupons_history`
**Purpose:** Coupon usage history
**Key Fields:** id, company_id, coupon_id, start_date, end_date
**Relationships:**
- `company_id` → `core_companies.id`
- `coupon_id` → `core_coupons.id`
**Use When:** Promotion tracking, discount analysis

### `credits`
**Purpose:** Candidate credit tracking
**Key Fields:** id, candidate_id, type, interview_id, credit
**Relationships:**
- `candidate_id` → `core_users_candidates.id`
- `interview_id` → `interviews.id`
**Use When:** Credit usage, candidate billing

### `packages`
**Purpose:** Candidate purchase packages
**Key Fields:** id, name, points, amount
**Use When:** Candidate purchase options, credit packages

---

## 8. INTEGRATION TABLES

### `integration_platforms`
**Purpose:** External platforms supported
**Key Fields:** id, name, slug, api_base_url, is_active
**Use When:** Platform configuration, integration setup

### `company_integrations_platforms`
**Purpose:** Company-specific integration settings
**Key Fields:** id, company_id, integration_platform_id, credentials, is_active
**Relationships:**
- `company_id` → `core_companies.id`
- `integration_platform_id` → `integration_platforms.id`
**Use When:** Company integration management, credential storage

### `integration_vacancies`
**Purpose:** Platform vacancy ID mapping
**Key Fields:** id, company_integration_id, platform_vacancy_id, company_vacancy_id
**Relationships:**
- `company_integration_id` → `company_integrations_platforms.id`
- `company_vacancy_id` → `vacancies.id`
**Use When:** Vacancy sync, ID mapping

### `integration_applicants`
**Purpose:** Platform applicant ID mapping
**Key Fields:** id, platform_applicant_id, company_vacancy_id, company_applicant_id
**Relationships:**
- `company_vacancy_id` → `vacancies.id`
- `company_applicant_id` → `vacancy_applicants.id`
**Use When:** Applicant sync, cross-platform tracking

### `integration_platform_logs`
**Purpose:** Integration sync logs
**Key Fields:** id, company_id, sync_type, status, error_message
**Relationships:** `company_id` → `core_companies.id`
**Use When:** Sync monitoring, error tracking

### `integration_job_logs`
**Purpose:** Individual job execution logs
**Key Fields:** id, integration_log_id, job_class, status, error_message
**Relationships:** `integration_log_id` → `integration_platform_logs.id`
**Use When:** Job-level debugging, performance monitoring

---

## 9. CRM & BOARD TABLES

### `crm_boards`
**Purpose:** Kanban boards for recruitment pipelines
**Key Fields:** id, title, status, company_id, entity_id
**Relationships:**
- `company_id` → `core_companies.id`
- `entity_id` → `core_entities.id`
**Use When:** Visual pipeline management, board setup

### `crm_board_columns`
**Purpose:** Columns within CRM boards
**Key Fields:** id, board_id, title, sort_order, color_code
**Relationships:** `board_id` → `crm_boards.id`
**Use When:** Column management, workflow stages

### `crm_board_applicants`
**Purpose:** Applicant positions in CRM boards
**Key Fields:** id, board_id, applicant_id, current_column_id, sort_index
**Relationships:**
- `board_id` → `crm_boards.id`
- `applicant_id` → `vacancy_applicants.id`
- `current_column_id` → `crm_board_columns.id`
**Use When:** Drag-drop operations, position tracking

---

## 10. COMMUNICATION & NOTIFICATION TABLES

### `core_notes`
**Purpose:** Notes on candidates, applications, vacancies
**Key Fields:** id, note, candidate_id, application_id, vacancy_id, created_by
**Relationships:**
- `candidate_id` → `core_users_candidates.id`
- `application_id` → `vacancy_applicants.id`
- `vacancy_id` → `vacancies.id`
- `created_by` → `core_users_recruiters.id`
**Use When:** Comments, internal communication, collaboration

### `core_note_contents`
**Purpose:** Content attachments for notes
**Key Fields:** id, note_id, content_id
**Relationships:**
- `note_id` → `core_notes.id`
- `content_id` → `core_contents.id`
**Use When:** Rich text notes, attachments

### `core_interactions`
**Purpose:** Activity logs and interactions
**Key Fields:** id, candidate_id, application_id, type, description, created_by
**Relationships:**
- `candidate_id` → `core_users_candidates.id`
- `application_id` → `vacancy_applicants.id`
- `created_by` → `core_users_recruiters.id`
**Use When:** Activity tracking, timeline generation

### `wa_contacts`
**Purpose:** WhatsApp contacts
**Key Fields:** id, wa_id, name
**Use When:** WhatsApp communication, contact management

### `wa_conversations`
**Purpose:** WhatsApp conversation threads
**Key Fields:** id, wa_contact_id, category, status
**Relationships:** `wa_contact_id` → `wa_contacts.id`
**Use When:** WhatsApp chat management

### `wa_messages`
**Purpose:** WhatsApp messages
**Key Fields:** id, wa_conversation_id, direction, type, text, status
**Relationships:** `wa_conversation_id` → `wa_conversations.id`
**Use When:** Message tracking, WhatsApp communication

### `companies_applicant_emails`
**Purpose:** Email communications with applicants
**Key Fields:** id, company_id, mail_type, from_mail, message_id, status
**Relationships:** `company_id` → `core_companies.id`
**Use When:** Email tracking, communication history

---

## 11. REPORTING & ANALYTICS TABLES

### `reports`
**Purpose:** Saved report definitions
**Key Fields:** id, title, type_id, query, json, views
**Relationships:**
- `type_id` → `report_types.id`
- `entity_id` → `core_entities.id`
**Use When:** Custom reports, saved queries

### `report_types`
**Purpose:** Report categories
**Key Fields:** id, name, description, entity_id
**Relationships:** `entity_id` → `core_entities.id`
**Use When:** Report classification

### `report_charts`
**Purpose:** Chart definitions within reports
**Key Fields:** id, report_id, title, type, json
**Relationships:** `report_id` → `reports.id`
**Use When:** Data visualization, dashboard charts

### `report_dashboards`
**Purpose:** Dashboard configurations
**Key Fields:** id, title, company_id, is_active
**Relationships:** `company_id` → `core_companies.id`
**Use When:** Dashboard creation, company views

### `report_dashboard_tiles`
**Purpose:** Tiles on dashboards
**Key Fields:** id, dashboard_id, chart_id, type
**Relationships:**
- `dashboard_id` → `report_dashboards.id`
- `chart_id` → `report_charts.id`
**Use When:** Dashboard layout, tile management

---

## 12. UTILITY & SYSTEM TABLES

### `core_tags`
**Purpose:** Tagging system for various entities
**Key Fields:** id, entity_id, company_id, tag
**Use When:** Categorization, search filtering

### `core_contents`
**Purpose:** Content storage for rich text
**Key Fields:** id, type, content, alt_name
**Use When:** Rich text content, HTML storage

### `core_errors`
**Purpose:** System error logging
**Key Fields:** id, type, error, status
**Use When:** Error tracking, debugging

### `failed_jobs`
**Purpose:** Failed job queue records
**Key Fields:** id, uuid, connection, queue, exception
**Use When:** Job failure analysis, retry management

### `jobs`
**Purpose:** Job queue records
**Key Fields:** id, queue, payload, attempts
**Use When:** Queue management, background processing

### `django_migrations`
**Purpose:** Django migration history
**Key Fields:** id, app, name, applied
**Use When:** Schema version tracking

### `django_content_type`
**Purpose:** Django content type registry
**Key Fields:** id, app_label, model
**Use When:** Generic relations, content type management

### `auth_permission`
**Purpose:** Django permission definitions
**Key Fields:** id, name, content_type_id, codename
**Relationships:** `content_type_id` → `django_content_type.id`
**Use When:** Permission management

---

## TABLE USAGE QUICK REFERENCE

| **Business Need** | **Primary Tables** |
|-------------------|-------------------|
| Find candidates by skill | `core_skills`, `candidate_skill_scores`, `core_users_candidates` |
| Track application status | `vacancy_applicants`, `vacancy_applicant_steps` |
| Analyze interview performance | `interviews`, `interview_results`, `interview_feedbacks` |
| Manage subscriptions | `core_companies`, `core_subscriptions`, `core_payments` |
| Configure interviews | `interview_configs`, `interview_config_skills`, `core_skills` |
| Generate reports | `reports`, `report_charts`, `report_dashboards` |
| Track integration syncs | `integration_platform_logs`, `integration_vacancies` |
| Candidate journey analysis | `core_users_candidates`, `vacancy_applicants`, `interviews` |
| Recruiter performance | `core_users_recruiters`, `interviews`, `vacancy_applicants` |
| AI evaluation quality | `llm_api_newconversation`, `llm_api_formquestionevaluation` |

---

## KEY RELATIONSHIPS SUMMARY

```
core_entities (central polymorphic hub)
    ↓
core_companies ← core_users_recruiters ← interviews ← interview_results
    ↓                    ↓
vacancies ← vacancy_applicants ← core_users_candidates
    ↓
vacancy_screening_steps ← vacancy_applicant_steps ← questionnaire_questions
    ↓
interview_configs ← interview_config_skills ← core_skills
```

This comprehensive guide should help you quickly identify which tables to use for specific business requirements in the Joboro platform.