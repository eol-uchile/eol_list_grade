"""
Module To Test EolListGrade XBlock
"""

from django.test import TestCase, Client
from mock import MagicMock, Mock, patch
from django.contrib.auth.models import User
from common.djangoapps.util.testing import UrlResetMixin
from opaque_keys.edx.locations import Location
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from common.djangoapps.student.roles import CourseStaffRole
from django.test.client import RequestFactory
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from common.djangoapps.student.tests.factories import UserFactory, CourseEnrollmentFactory
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
        xblock.location = course.location
        xblock.course_id = course.id
        xblock.category = 'eollistgrade'
        return xblock

    def setUp(self):
        super(EolListGradeXBlockTestCase, self).setUp()
        """
        Creates an xblock
        """
        self.course = CourseFactory.create(org='foo', course='baz', run='bar')

        self.xblock = self.make_an_xblock()

        with patch('common.djangoapps.student.models.cc.User.save'):
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
            Verify if default xblock is created correctly
        """
        self.assertEqual(self.xblock.display_name, 'Notas Manuales')
        self.assertEqual(self.xblock.puntajemax, 100)

    def test_edit_block_studio(self):
        """
            Verify submit studio edits is working
        """
        request = TestRequest()
        request.method = 'POST'
        self.xblock.xmodule_runtime.user_is_staff = True
        data = json.dumps({'display_name': 'testname', "puntajemax": '200'})
        request.body = data.encode()
        response = self.xblock.studio_submit(request)
        self.assertEqual(self.xblock.display_name, 'testname')
        self.assertEqual(self.xblock.puntajemax, 200)

    def test_student_view_staff(self):
        """
            Verify context in student_view staff user
        """
        context_student = {'id': self.student.id,
                            'username': self.student.username,
                            'correo': self.student.email,
                            'pun': '',
                            'com': ''}
        context_staff = {'id': self.staff_user.id,
                            'username': self.staff_user.username,
                            'correo': self.staff_user.email,
                            'pun': '',
                            'com': ''}
        self.xblock.xmodule_runtime.user_is_staff = True
        self.xblock.scope_ids.user_id = self.staff_user.id
        response = self.xblock.get_context()
        self.assertEqual(response['is_course_staff'], True)
        self.assertEqual(response['calificado_total'], 0)
        self.assertEqual(response['calificado_alumnos'], 0)
        self.assertEqual(response['calificado_equipo'], 0)
        self.assertEqual(response['lista_alumnos'][0], context_student)
        self.assertEqual(response['lista_equipo'][0], context_staff)

    def test_student_view_student(self):
        """
            Verify context in student_view student user
        """
        context_student = {'id': self.student.id,
                            'username': self.student.username,
                            'correo': self.student.email,
                            'pun': '',
                            'com': ''}
        self.xblock.xmodule_runtime.user_is_staff = False
        self.xblock.scope_ids.user_id = self.student.id
        response = self.xblock.get_context()
        self.assertEqual(response['is_course_staff'], False)
        self.assertEqual(response['comentario'], '')
        self.assertEqual(response['puntaje'], '')

    @patch('lms.djangoapps.grades.signals.handlers.PROBLEM_WEIGHTED_SCORE_CHANGED.send')
    def test_student_view_staff_with_data(self, _):
        """
            Verify context in student_view staff user with data
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "11",
                           "comentario": "comentario121",
                           "role": 'estudiante'})
        request.body = data.encode()
        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()

        aux_response = self.xblock.savestudentanswers(request)
        context_student = {'id': self.student.id,
                            'username': self.student.username,
                            'correo': self.student.email,
                            'pun': 11,
                            'com': 'comentario121'}
        context_staff = {'id': self.staff_user.id,
                            'username': self.staff_user.username,
                            'correo': self.staff_user.email,
                            'pun': '',
                            'com': ''}
        self.xblock.xmodule_runtime.user_is_staff = True
        self.xblock.scope_ids.user_id = self.staff_user.id
        response = self.xblock.get_context()
        self.assertEqual(response['is_course_staff'], True)
        self.assertEqual(response['calificado_total'], 1)
        self.assertEqual(response['calificado_alumnos'], 1)
        self.assertEqual(response['calificado_equipo'], 0)
        self.assertEqual(response['lista_alumnos'][0], context_student)
        self.assertEqual(response['lista_equipo'][0], context_staff)

    @patch('lms.djangoapps.grades.signals.handlers.PROBLEM_WEIGHTED_SCORE_CHANGED.send')
    def test_student_view_student_with_data(self, _):
        """
            Verify context in student_view student user with data
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "11",
                           "comentario": "comentario121",
                           "role": 'estudiante'})
        request.body = data.encode()
        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()

        aux_response = self.xblock.savestudentanswers(request)
        context_student = {'id': self.student.id,
                            'username': self.student.username,
                            'correo': self.student.email,
                            'pun': '11',
                            'com': 'comentario121'}
        self.xblock.xmodule_runtime.user_is_staff = False
        self.xblock.scope_ids.user_id = self.student.id
        response = self.xblock.get_context()
        self.assertEqual(response['is_course_staff'], False)
        self.assertEqual(response['comentario'], 'comentario121')
        self.assertEqual(response['puntaje'], 11)

    @patch('lms.djangoapps.grades.signals.handlers.PROBLEM_WEIGHTED_SCORE_CHANGED.send')
    def test_save_staff_user(self, _):
        """
          Save score and comment by staff user
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "11",
                           "comentario": "comentario121",
                           "role": 'estudiante'})
        request.body = data.encode()
        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()

        response = self.xblock.savestudentanswers(request)
        state = StudentModule.objects.get(pk=module.id)
        self.assertEqual(
            json.loads(state.state),
            json.loads('{"comment": "comentario121", "student_score": 11}'))
        self.assertEqual(self.xblock.get_score(self.student.id), 11)

    def test_save_student_user(self):
        """
          Save score and comment by student user
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = False

        data = json.dumps({"id": self.student.id,
                           "puntaje": "11",
                           "comentario": "comentario121",
                           "role": 'estudiante'})
        request.body = data.encode()
        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()
        response = self.xblock.savestudentanswers(request)
        state = StudentModule.objects.get(pk=module.id)
        self.assertEqual(json.loads(state.state), json.loads('{}'))
        self.assertEqual(self.xblock.get_score(self.student.id), None)

    @patch('lms.djangoapps.grades.signals.handlers.PROBLEM_WEIGHTED_SCORE_CHANGED.send')
    def test_saveall_staff_user(self, _):
        """
          Save score and comment of all students by staff user
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True
        datos = [[self.student.id, "11", "com1"],
                 [self.staff_user.id, "22", "com2"]]
        data = json.dumps({"data": datos})
        request.body = data.encode()

        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()

        module_staff = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.staff_user.id,
            course_id=self.course.id,
            state='{}')
        module_staff.save()

        response = self.xblock.savestudentanswersall(request)
        state = StudentModule.objects.get(pk=module.id)
        state_staff = StudentModule.objects.get(pk=module_staff.id)

        self.assertEqual(
            json.loads(state.state),
            json.loads('{"comment": "com1", "student_score": 11}'))
        self.assertEqual(
            json.loads(state_staff.state),
            json.loads('{"comment": "com2", "student_score": 22}'))
        self.assertEqual(self.xblock.get_score(self.student.id), 11)
        self.assertEqual(self.xblock.get_score(self.staff_user.id), 22)

    def test_saveall_student_user(self):
        """
          Save score and comment of all students by student user
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = False

        datos = [[self.student.id, "11", "com1"],
                 [self.staff_user.id, "22", "com2"]]
        data = json.dumps({"data": datos})
        request.body = data.encode()

        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()

        module_staff = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.staff_user.id,
            course_id=self.course.id,
            state='{}')
        module_staff.save()

        response = self.xblock.savestudentanswersall(request)
        state = StudentModule.objects.get(pk=module.id)
        state_staff = StudentModule.objects.get(pk=module_staff.id)
        self.assertEqual(json.loads(state.state), json.loads('{}'))
        self.assertEqual(state_staff.state, '{}')
        self.assertEqual(self.xblock.get_score(self.student.id), None)
        self.assertEqual(self.xblock.get_score(self.staff_user.id), None)

    def test_wrong_data_staff_user(self):
        """
          Save score and comment by staff user with wrong score
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "asd",
                           "comentario": "comentario121",
                           "role": 'estudiante'})
        request.body = data.encode()
        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()
        response = self.xblock.savestudentanswers(request)
        data_response = json.loads(response._app_iter[0].decode())
        state = StudentModule.objects.get(pk=module.id)
        self.assertEqual(json.loads(state.state), json.loads('{}'))
        self.assertEqual(self.xblock.get_score(self.student.id), None)
        self.assertEqual(data_response['result'], 'error')

    def test_wrong_data_staff_user_2(self):
        """
          Save score and comment by staff user with wrong params
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "role": 'estudiante'})
        request.body = data.encode()
        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()
        response = self.xblock.savestudentanswers(request)
        state = StudentModule.objects.get(pk=module.id)
        self.assertEqual(json.loads(state.state), json.loads('{}'))
        self.assertEqual(self.xblock.get_score(self.student.id), None)

    @patch('lms.djangoapps.grades.signals.handlers.PROBLEM_WEIGHTED_SCORE_CHANGED.send')
    def test_save_student_score_max_score(self, _):
        """
          Save score and comment by staff user with score = max score
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": self.xblock.puntajemax,
                           "comentario": "comentario121",
                           "role": 'estudiante'})
        request.body = data.encode()
        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()
        response = self.xblock.savestudentanswers(request)
        state = StudentModule.objects.get(pk=module.id)
        self.assertEqual(
            json.loads(state.state),
            json.loads('{"comment": "comentario121", "student_score": 100}'))
        self.assertEqual(self.xblock.get_score(self.student.id), 100)

    @patch('lms.djangoapps.grades.signals.handlers.PROBLEM_WEIGHTED_SCORE_CHANGED.send')
    def test_save_student_score_min_score(self, _):
        """
          Save score and comment by staff user with score = 0
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "0",
                           "comentario": "comentario121",
                           "role": 'estudiante'})
        request.body = data.encode()
        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()
        response = self.xblock.savestudentanswers(request)
        state = StudentModule.objects.get(pk=module.id)
        self.assertEqual(
            json.loads(state.state),
            json.loads('{"comment": "comentario121", "student_score": 0}'))
        self.assertEqual(self.xblock.get_score(self.student.id), 0)

    def test_save_student_score_min_score_wrong(self):
        """
          Save score and comment by staff user with score < 0
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "-1",
                           "comentario": "comentario121",
                           "role": 'estudiante'})
        request.body = data.encode()
        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()
        response = self.xblock.savestudentanswers(request)
        state = StudentModule.objects.get(pk=module.id)
        self.assertEqual(json.loads(state.state), json.loads('{}'))
        self.assertEqual(self.xblock.get_score(self.student.id), None)

    def test_save_student_score_max_score_wrong(self):
        """
          Save score and comment by staff user with score > max score
        """
        from lms.djangoapps.courseware.models import StudentModule
        request = TestRequest()
        request.method = 'POST'

        self.xblock.xmodule_runtime.user_is_staff = True

        data = json.dumps({"id": self.student.id,
                           "puntaje": "101",
                           "comentario": "comentario121",
                           "role": 'estudiante'})
        request.body = data.encode()
        module = StudentModule(
            module_state_key=self.xblock.location,
            student_id=self.student.id,
            course_id=self.course.id,
            state='{}')
        module.save()
        response = self.xblock.savestudentanswers(request)
        state = StudentModule.objects.get(pk=module.id)
        self.assertEqual(json.loads(state.state), json.loads('{}'))
        self.assertEqual(self.xblock.get_score(self.student.id), None)
