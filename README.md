# EOL List Grade

![https://github.com/eol-uchile/eol_list_grade/actions](https://github.com/eol-uchile/eol_list_grade/workflows/Python%20application/badge.svg)

This XBlock allow to assign score and comments each students.

# Install

    docker-compose exec cms pip install -e /openedx/requirements/eol_list_grade
    docker-compose exec lms pip install -e /openedx/requirements/eol_list_grade

## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run --rm lms /openedx/requirements/eol_list_grade/.github/test.sh