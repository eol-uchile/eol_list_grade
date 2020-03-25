"""
Module To Test EolListGrade XBlock
"""
from openedx.core.lib.tests.tools import assert_true

from django.test import TestCase, Client
from mock import MagicMock, Mock, patch
from django.contrib.auth.models import User
from util.testing import UrlResetMixin
from opaque_keys.edx.locations import Location
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from student.roles import CourseStaffRole
from django.test.client import RequestFactory
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from student.tests.factories import UserFactory, CourseEnrollmentFactory
from lms.djangoapps.courseware.tests.factories import StudentModuleFactory
from xblock.field_data import DictFieldData
from opaque_keys.edx.locator import CourseLocator
from .eollistgrade import EolListGradeXBlock

import json
import unittest
import logging
import mock

log = logging.getLogger(__name__)


class TestRequest(object):
    # pylint: disable=too-few-public-methods
    """
    Module helper for @json_handler
    """
    method = None
    body = None
    success = None


def fake_student_module():
    """dummy representation of xblock class"""
    return mock.Mock(
        course_id=CourseLocator(
            org='foo',
            course='baz',
            run='bar'),
        module_state_key="foo",
        student_id=mock.Mock(
            username="fred6",
            is_staff=False,
            password="test"),
        state='{}',
        save=mock.Mock())


class EolListGradeXBlockTestCase(UrlResetMixin, ModuleStoreTestCase):
    # pylint: disable=too-many-instance-attributes, too-many-public-methods
    """
    A complete suite of unit tests for the EolListGrade XBlock
    """

    def make_an_xblock(cls, **kw):
        """
        Helper method that creates a EolListGrade XBlock
        """

        course = cls.course
        runtime = Mock(
            course_id=course.id,
            user_is_staff=False,
            service=Mock(
                return_value=Mock(_catalog={}),
            ),
        )
        scope_ids = Mock()
        field_data = DictFieldData(kw)
        xblock = EolListGradeXBlock(runtime, field_data, scope_ids)
        xblock.xmodule_runtime = runtime
        xblock.location = course.id
        xblock.course_id = course.location
        xblock.category = 'eollistgrade'
        return xblock

    def setUp(self):
        super(EolListGradeXBlockTestCase, self).setUp()
        """
        Creates an xblock
        """
        self.course = CourseFactory.create(org='foo', course='baz', run='bar')

        self.xblock = self.make_an_xblock()

        with patch('student.models.cc.User.save'):
            # Create the student
            self.student = UserFactory(
                username='student',
                password='test',
                email='student@edx.org')
            # Enroll the student in the course
            CourseEnrollmentFactory(
                user=self.student, course_id=self.course.id)

            # Create staff user
            self.staff_user = UserFactory(
                username='staff_user',
                password='test',
                email='staff@edx.org')
            CourseEnrollmentFactory(
                user=self.staff_user,
                course_id=self.course.id)
            CourseStaffRole(self.course.id).add_users(self.staff_user)

    def test_validate_field_data(self):
        """
        Reviso si se creo bien el xblock por defecto.
        """
        self.assertEqual(self.xblock.display_name, 'Eol List Grade XBlock')
        self.assertEqual(self.xblock.puntajemax, 100)

    def test_edit_block_studio(self):
        """
        Reviso que este funcionando el submit studio edits
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "puntajemax": '200'})
        request.body = data
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'testname')
        self.assertEqual(self.xblock.puntajemax, 200)

    def test_save_staff_user(self):
        """
        Checks the student view for student specific instance variables.
        """
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "11",
                           "comentario": "comentario121"})
        request.body = data
        module = fake_student_module()
        with mock.patch('eollistgrade.eollistgrade.EolListGradeXBlock.get_or_create_student_module', return_value=module):
            response = self.xblock.savestudentanswers(request)

        self.assertEqual(
            module.state,
            '{"comment": "comentario121", "student_score": 11}')
        self.assertEqual(self.xblock.get_score(self.student.id), 11)

    def test_save_student_user(self):
        """
        Checks the student view for student specific instance variables.
        """
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = False

        data = json.dumps({"id": self.student.id,
                           "puntaje": "11",
                           "comentario": "comentario121"})
        request.body = data
        module = fake_student_module()
        with mock.patch('eollistgrade.eollistgrade.EolListGradeXBlock.get_or_create_student_module', return_value=module):
            response = self.xblock.savestudentanswers(request)

        self.assertEqual(module.state, '{}')
        self.assertEqual(self.xblock.get_score(self.student.id), None)

    def test_saveall_staff_user(self):
        """
        Checks the student view for student specific instance variables.
        """
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True
        datos = [[self.student.id, "11", "com1"],
                 [self.staff_user.id, "22", "com2"]]
        data = json.dumps({"data": datos})
        request.body = data
        module = fake_student_module()
        with mock.patch('eollistgrade.eollistgrade.EolListGradeXBlock.get_or_create_student_module', return_value=module):
            response = self.xblock.savestudentanswersall(request)

        self.assertEqual(
            module.state,
            '{"comment": "com2", "student_score": 22}')
        self.assertEqual(self.xblock.get_score(self.student.id), 11)
        self.assertEqual(self.xblock.get_score(self.staff_user.id), 22)

    def test_saveall_student_user(self):
        """
        Checks the student view for student specific instance variables.
        """
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = False

        datos = [[self.student.id, "11", "com1"],
                 [self.staff_user.id, "22", "com2"]]
        data = json.dumps({"data": datos})
        request.body = data
        module = fake_student_module()
        with mock.patch('eollistgrade.eollistgrade.EolListGradeXBlock.get_or_create_student_module', return_value=module):
            response = self.xblock.savestudentanswersall(request)

        self.assertEqual(module.state, '{}')
        self.assertEqual(self.xblock.get_score(self.student.id), None)
        self.assertEqual(self.xblock.get_score(self.staff_user.id), None)

    def test_wrong_data_staff_user(self):
        """
        Checks the student view for student specific instance variables.
        """
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "asd",
                           "comentario": "comentario121"})
        request.body = data
        module = fake_student_module()
        with mock.patch('eollistgrade.eollistgrade.EolListGradeXBlock.get_or_create_student_module', return_value=module):
            response = self.xblock.savestudentanswers(request)

        self.assertEqual(module.state, '{}')
        self.assertEqual(self.xblock.get_score(self.student.id), None)

    def test_save_student_score_max_score(self):
        """
        Checks the student view for student specific instance variables.
        """
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": self.xblock.puntajemax,
                           "comentario": "comentario121"})
        request.body = data
        module = fake_student_module()
        with mock.patch('eollistgrade.eollistgrade.EolListGradeXBlock.get_or_create_student_module', return_value=module):
            response = self.xblock.savestudentanswers(request)

        self.assertEqual(
            module.state,
            '{"comment": "comentario121", "student_score": 100}')
        self.assertEqual(self.xblock.get_score(self.student.id), 100)

    def test_save_student_score_min_score(self):
        """
        Checks the student view for student specific instance variables.
        """
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "0",
                           "comentario": "comentario121"})
        request.body = data
        module = fake_student_module()
        with mock.patch('eollistgrade.eollistgrade.EolListGradeXBlock.get_or_create_student_module', return_value=module):
            response = self.xblock.savestudentanswers(request)

        self.assertEqual(
            module.state,
            '{"comment": "comentario121", "student_score": 0}')
        self.assertEqual(self.xblock.get_score(self.student.id), 0)

    def test_save_student_score_min_score_wrong(self):
        """
        Checks the student view for student specific instance variables.
        """
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "-1",
                           "comentario": "comentario121"})
        request.body = data
        module = fake_student_module()
        with mock.patch('eollistgrade.eollistgrade.EolListGradeXBlock.get_or_create_student_module', return_value=module):
            response = self.xblock.savestudentanswers(request)

        self.assertEqual(module.state, '{}')
        self.assertEqual(self.xblock.get_score(self.student.id), None)

    def test_save_student_score_max_score_wrong(self):
        """
        Checks the student view for student specific instance variables.
        """
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "101",
                           "comentario": "comentario121"})
        request.body = data
        module = fake_student_module()
        with mock.patch('eollistgrade.eollistgrade.EolListGradeXBlock.get_or_create_student_module', return_value=module):
            response = self.xblock.savestudentanswers(request)

        self.assertEqual(module.state, '{}')
        self.assertEqual(self.xblock.get_score(self.student.id), None)
