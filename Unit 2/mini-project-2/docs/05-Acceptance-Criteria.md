# 5. Acceptance Criteria

Acceptance criteria define the conditions that must be satisfied for a user story to be accepted.

## US-01 — User Login
- The login page is available to the user.
- A registered user can sign in with valid credentials.
- Invalid credentials show a clear error message.
- Successful login opens the appropriate page for the user's role.
- A session is managed safely and can be ended by logging out.

## US-03 — Add Student
- An authorized user can open the student registration form.
- Required fields are validated before saving.
- The system prevents or flags duplicate student identifiers.
- A valid student record is saved successfully.
- A confirmation message is displayed after saving.

## US-04 — Search Student
- An authorized user can search using an available identifier or name.
- Matching records are displayed clearly.
- A no-results message appears when no matching record exists.
- Users without permission cannot access protected student information.

## US-05 — Update Student
- An authorized user can open an existing student record.
- Editable fields can be changed.
- Required-field validation is applied.
- Updated details are saved and shown when the record is viewed again.

## US-07 — Add Course
- An authorized user can enter course details.
- Required fields are validated.
- Duplicate course identifiers are prevented or flagged.
- A valid course is saved and appears in the course list.

## US-09 — Record Attendance
- Faculty can select a course and lecture date.
- The enrolled student list is shown for that course.
- Faculty can mark each student present or absent.
- The attendance record is saved successfully.
- The system provides confirmation and allows saved records to be reviewed.

## US-11 — Enter Marks
- Authorized faculty can select the relevant course and assessment.
- Marks must follow the configured valid range.
- Valid marks are saved against the correct student and assessment.
- Invalid marks are rejected with a clear message.
- Only authorized users can change marks.

## US-13 — Generate Reports
- An authorized user can choose an available report type.
- The report uses saved records.
- The report displays the selected data in a readable format.
- Empty results are handled with a clear message.

## Definition of Done
A story is Done when its acceptance criteria pass, relevant tests are completed, documentation is updated where needed, and the increment is reviewed by the team.
