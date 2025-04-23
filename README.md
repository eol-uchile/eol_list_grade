# EOL List Grade

![Coverage Status](/coverage-badge.svg)

![https://github.com/eol-uchile/eol_list_grade/actions](https://github.com/eol-uchile/eol_list_grade/workflows/Python%20application/badge.svg)

This XBlock allow to assign score and comments each students.

# Install

    docker-compose exec cms pip install -e /openedx/requirements/eol_list_grade
    docker-compose exec lms pip install -e /openedx/requirements/eol_list_grade

## TESTS
**Prepare tests:**

- Install **act** following the instructions in [https://nektosact.com/installation/index.html](https://nektosact.com/installation/index.html)

**Run tests:**
- In a terminal at the root of the project
    ```
    act -W .github/workflows/pythonapp.yml
    ```
