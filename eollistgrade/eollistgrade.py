import pkg_resources
import six
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request
import logging
import json

from django.template import Context, Template

from xblock.core import XBlock
from xblock.fields import Integer, Scope, String, Dict
from xblock.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin
from opaque_keys.edx.keys import CourseKey, UsageKey
from lms.djangoapps.courseware.courses import get_course_with_access

from django.contrib.auth.models import User
from submissions import api as submissions_api
from student.models import user_by_anonymous_id
from courseware.models import StudentModule

log = logging.getLogger(__name__)
# Make '_' a no-op so we can scrape strings


def _(text): return text


def reify(meth):
    """
    Decorator which caches value so it is only computed once.
    Keyword arguments:
    inst
    """
    def getter(inst):
        """
        Set value to meth name in dict and returns value.
        """
        value = meth(inst)
        inst.__dict__[meth.__name__] = value
        return value
    return property(getter)


class EolListGradeXBlock(StudioEditableXBlockMixin, XBlock):

    display_name = String(
        display_name=_("Display Name"),
        help=_("Display name for this module"),
        default="Eol List Grade XBlock",
        scope=Scope.settings,
    )
    puntajemax = Integer(
        display_name='Puntaje Maximo',
        help='Entero que representa puntaje maximo',
        default=100,
        values={'min': 1},
        scope=Scope.user_state,
    )

    has_author_view = True

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    @reify
    def block_course_id(self):
        """
        Return the course_id of the block.
        """
        return six.text_type(self.course_id)

    @reify
    def block_id(self):
        """
        Return the usage_id of the block.
        """
        return six.text_type(self.scope_ids.usage_id)

    def is_course_staff(self):
        # pylint: disable=no-member
        """
         Check if user is course staff.
        """
        return getattr(self.xmodule_runtime, 'user_is_staff', False)

    def is_instructor(self):
        # pylint: disable=no-member
        """
        Check if user role is instructor.
        """
        return self.xmodule_runtime.get_user_role() == 'instructor'

    def show_staff_grading_interface(self):
        """
        Return if current user is staff and not in studio.
        """
        in_studio_preview = self.scope_ids.user_id is None
        return self.is_course_staff() and not in_studio_preview

    def get_submission(self, student_id=None):
        """
        Get student's most recent submission.
        """
        submissions = submissions_api.get_submissions(
            self.get_student_item_dict(student_id)
        )
        if submissions:
            # If I understand docs correctly, most recent submission should
            # be first
            return submissions[0]

    def get_student_item_dict(self, student_id=None):
        # pylint: disable=no-member
        """
        Returns dict required by the submissions app for creating and
        retrieving submissions for a particular student.
        """
        if student_id is None:
            student_id = self.xmodule_runtime.anonymous_student_id
            assert student_id != (
                'MOCK', "Forgot to call 'personalize' in test."
            )
        return {
            "student_id": student_id,
            "course_id": self.block_course_id,
            "item_id": self.block_id,
            "item_type": 'problem',
        }

    def get_score(self, student_id=None):
        """
        Return student's current score.
        """
        score = submissions_api.get_score(
            self.get_student_item_dict(student_id)
        )
        if score:
            return score['points_earned']

    def get_com(self, student_id, course_key, block_key):
        """
        Return student's comments
        """

        try:
            student_module = StudentModule.objects.get(
                student_id=student_id,
                course_id=self.course_id,
                module_state_key=self.location
            )
        except StudentModule.DoesNotExist:
            student_module = None

        if student_module:
            return json.loads(student_module.state)
        return {}

    def get_or_create_student_module(self, student_id):
        """
        Gets or creates a StudentModule for the given user for this block
        Returns:
            StudentModule: A StudentModule object
        """
        # pylint: disable=no-member
        
        student_module, created = StudentModule.objects.get_or_create(
            course_id= self.course_id,
            module_state_key=self.location,
            student_id=student_id,
            defaults={
                'state': '{}',
                'module_type': self.category,
            }
        )
        if created:
            log.info(
                "Created student module %s [course: %s] [student: %s]",
                student_module.module_state_key,
                student_module.course_id,
                student_module.student.username
            )
        return student_module

    def author_view(self, context=None):
        context = {'xblock': self, 'location': str(
            self.location).split('@')[-1]}
        template = self.render_template(
            'static/html/author_view.html', context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/eollistgrade.css"))
        return frag

    def studio_view(self, context=None):
        context = {'xblock': self,
                   'location': str(self.location).split('@')[-1],
                   'display_name': self.display_name}
        template = self.render_template(
            'static/html/studio_view.html', context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/eollistgrade.css"))
        frag.add_javascript(self.resource_string(
            "static/js/src/eollistgrade_studio.js"))
        frag.initialize_js('EolListGradeXBlock')
        return frag

    def student_view(self, context=None):
        context = self.get_context()
        template = self.render_template(
            'static/html/eollistgrade.html', context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/eollistgrade.css"))
        frag.add_javascript(self.resource_string(
            "static/js/src/eollistgrade.js"))
        frag.initialize_js('EolListGradeXBlock')
        return frag

    def get_context(self):
        aux = self.block_course_id
        course_key = CourseKey.from_string(aux)
        enrolled_students = User.objects.filter(
            courseenrollment__course_id=course_key,
            courseenrollment__is_active=1
        ).order_by('username').values('id', 'username', 'email')
        context = {'xblock': self}
        lista_alumnos = []
        calificado = 0
        if self.show_staff_grading_interface():
            for a in enrolled_students:
                p = ''
                if self.get_score(a['id']):
                    p = self.get_score(a['id'])
                    calificado = calificado + 1

                state = self.get_com(a['id'], course_key, self.block_id)
                com = ''
                if 'comment' in state:
                    com = state['comment']
                lista_alumnos.append({'id': a['id'],
                                      'username': a['username'],
                                      'correo': a['email'],
                                      'pun': p,
                                      'com': com})

            context['lista_alumnos'] = lista_alumnos
            context['calificado'] = calificado
            context['category'] = type(self).__name__
            context['is_course_staff'] = True
        else:
            enrolled_student = User.objects.filter(
                courseenrollment__course_id=course_key,
                courseenrollment__is_active=1,
                id=self.scope_ids.user_id
            ).values('id', 'username', 'email').first()
            p = '0'
            if self.get_score(enrolled_student['id']):
                p = self.get_score(enrolled_student['id'])

            state = self.get_com(
                enrolled_student['id'],
                course_key,
                self.block_id)
            com = ''
            if 'comment' in state:
                com = state['comment']

            context['puntaje'] = p
            context['comentario'] = com
            context['usuario'] = enrolled_student
            context['is_course_staff'] = False
        return context

    def validar_datos(self, data):
        return data.get('puntaje').lstrip('+').isdigit() and data.get('puntajemax').lstrip('+').isdigit()

    def validar_datos_all(self, data):
        score = True
        for fila in data.get('data'):
            if not fila[1].lstrip('+').isdigit():
                score = False
                break
        return score and data.get('puntajemax').lstrip('+').isdigit()
        
    @XBlock.json_handler
    def savestudentanswers(self, data, suffix=''):
        valida = self.validar_datos(data)
        if self.show_staff_grading_interface() and valida:
            student_module = self.get_or_create_student_module(data.get('id'))
            state = json.loads(student_module.state)
            score = int(data.get('puntaje'))
            state['comment'] = data.get('comentario')
            state['student_score'] = score
            state['score_max'] = data.get('puntajemax')
            student_module.state = json.dumps(state)
            student_module.save()
            self.puntajemax = int(data.get('puntajemax'))
            student_item = {
                'student_id': data.get('id'),
                'course_id': self.block_course_id,
                'item_id': self.block_id,
                'item_type': 'problem'
            }
            submission = self.get_submission(data.get('id'))
            if submission:
                submissions_api.set_score(
                    submission['uuid'], score, int(data.get('puntajemax')))
            else:
                submission = submissions_api.create_submission(
                    student_item, 'any answer')
                submissions_api.set_score(
                    submission['uuid'], score, int(
                        data.get('puntajemax')))

            return {'result': 'success', 'id': data.get('id')}
        
        return {'result': 'error'}

    @XBlock.json_handler
    def savestudentanswersall(self, data, suffix=''):
        valida = self.validar_datos_all(data)
        if self.show_staff_grading_interface() and valida:
            self.puntajemax = int(data.get('puntajemax'))
            for fila in data.get('data'):
                student_module = self.get_or_create_student_module(fila[0])
                state = json.loads(student_module.state)
                score = int(fila[1])
                state['comment'] = fila[2]
                state['student_score'] = score
                state['score_max'] = data.get('puntajemax')
                student_module.state = json.dumps(state)
                student_module.save()

                student_item = {
                    'student_id': fila[0],
                    'course_id': self.block_course_id,
                    'item_id': self.block_id,
                    'item_type': 'problem'
                }
                submission = self.get_submission(fila[0])
                if submission:
                    submissions_api.set_score(
                        submission['uuid'], score, int(data.get('puntajemax')))
                else:
                    submission = submissions_api.create_submission(
                        student_item, 'any answer')
                    submissions_api.set_score(
                        submission['uuid'], score, int(
                            data.get('puntajemax')))

            return {'result': 'success', 'id': '00'}
        
        return {'result': 'error'}

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Called when submitting the form in Studio.
        """
        self.display_name = data.get('display_name') or ""

        return {'result': 'success'}

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

        # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("EolListGradeXBlock",
             """<eollistgrade/>
             """),
            ("Multiple EolListGradeXBlock",
             """<vertical_demo>
                <eollistgrade/>
                <eollistgrade/>
                <eollistgrade/>
                </vertical_demo>
             """),
        ]
