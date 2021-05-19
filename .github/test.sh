#!/bin/dash

pip install -e /openedx/requirements/eol_list_grade

cd /openedx/requirements/eol_list_grade
cp /openedx/edx-platform/setup.cfg .
mkdir test_root
cd test_root/
ln -s /openedx/staticfiles .

cd /openedx/requirements/eol_list_grade

DJANGO_SETTINGS_MODULE=lms.envs.test EDXAPP_TEST_MONGO_HOST=mongodb pytest eollistgrade/tests.py
