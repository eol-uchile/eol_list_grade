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
from lms.djangoapps.courseware.models import StudentModule

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
        values={'min': 0},
        scope=Scope.settings,
    )

    has_author_view = True
    has_score = True

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

    def get_anonymous_id(self, student_id=None):
        """
            Return anonymous id
        """
        from student.models import anonymous_id_for_user

        course_key = self.course_id
        return anonymous_id_for_user(User.objects.get(id=student_id), course_key)

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
        anonymous_user_id = self.get_anonymous_id(student_id)
        score = submissions_api.get_score(
            self.get_student_item_dict(anonymous_user_id)
        )
        if score:
            return score['points_earned']
        else:
            return None

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

    def get_all_student_module(self, course_key, block_key):
        """
        Return student's comments
        """
        try:
            student_modules = StudentModule.objects.filter(
                course_id=self.course_id,
                module_state_key=self.location
            )
        except StudentModule.DoesNotExist:
            student_modules = None

        if student_modules:
            all_modules = {}
            for module in student_modules:
                all_modules[str(module.student_id)] = json.loads(module.state)
            return all_modules
        return {}

    def get_or_create_student_module(self, student_id):
        """
        Gets or creates a StudentModule for the given user for this block
        Returns:
            StudentModule: A StudentModule object
        """
        # pylint: disable=no-member

        student_module, created = StudentModule.objects.get_or_create(
            course_id=self.course_id,
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
                   'location': str(self.location).split('@')[-1]}
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
        course_key = self.course_id
        enrolled_students = User.objects.filter(
            courseenrollment__course_id=course_key,
            courseenrollment__is_active=1
        ).order_by('username').values('id', 'username', 'email')
        filter_all_sub = {}
        for student_item, submission, score in all_submission:
            filter_all_sub[student_item['student_id']] = score['points_earned']
        context = {'xblock': self}
        lista_alumnos = []
        calificado = 0
        if self.show_staff_grading_interface():
            for a in enrolled_students:
                p = ''
                anonymous_id = self.get_anonymous_id(a['id'])
                if anonymous_id in filter_all_sub:
                    if filter_all_sub[anonymous_id] is not None and filter_all_sub[anonymous_id] >= 0:
                        p = filter_all_sub[anonymous_id]
                        calificado = calificado + 1

                states = self.get_all_student_module(course_key, self.block_id)
                
                com = ''
                if a['id'] in states:
                    if 'comment' in states[a['id']]:
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
            p = ''
            com = ''
            aux_pun = self.get_score(self.scope_ids.user_id)
            if aux_pun is not None and aux_pun >= 0:
                p = aux_pun
                state = self.get_com(
                    self.scope_ids.user_id,
                    course_key,
                    self.block_id)

                if 'comment' in state:
                    com = state['comment']

            context['puntaje'] = p
            context['comentario'] = com
            context['is_course_staff'] = False
        return context

    def validar_datos(self, data):
        """
            Verify if data is valid per student
        """
        return str(
            data.get('puntaje')).lstrip('+').isdigit() and int(
            data.get('puntaje')) >= 0 and int(
            data.get('puntaje')) <= self.puntajemax

    def validar_datos_all(self, data):
        """
            Verify if all students data is valid
        """
        score = True
        for fila in data.get('data'):
            if not str(fila[1]).lstrip('+').isdigit() or int(fila[1]
                                                             ) < 0 or int(fila[1]) > self.puntajemax:
                score = False
                break
        return score

    def max_score(self):
        return self.puntajemax

    @XBlock.json_handler
    def savestudentanswers(self, data, suffix=''):
        """
            Save the score and comment per student
        """
        valida = self.validar_datos(data)
        if self.show_staff_grading_interface() and valida:
            calificado = True
            student_module = self.get_or_create_student_module(data.get('id'))
            state = json.loads(student_module.state)
            score = int(data.get('puntaje'))
            state['comment'] = data.get('comentario')
            state['student_score'] = score
            student_module.state = json.dumps(state)
            student_module.save()
            
            from student.models import anonymous_id_for_user
            
            course_key = self.course_id
            anonymous_user_id = anonymous_id_for_user(User.objects.get(id=int(data.get('id'))), course_key)
            student_item = {
                'student_id': anonymous_user_id,
                'course_id': self.block_course_id,
                'item_id': self.block_id,
                'item_type': 'problem'
            }

            submission = self.get_submission(anonymous_user_id)
            if submission:
                submissions_api.set_score(
                    submission['uuid'], score, self.puntajemax)
            else:
                calificado = False
                submission = submissions_api.create_submission(
                    student_item, 'any answer')
                submissions_api.set_score(
                    submission['uuid'], score, self.puntajemax)

            return {
                'result': 'success',
                'id': data.get('id'),
                'calificado': calificado}

        return {'result': 'error'}

    @XBlock.json_handler
    def savestudentanswersall(self, data, suffix=''):
        """
            Save the score and comment of all students
        """
        valida = self.validar_datos_all(data)
        if self.show_staff_grading_interface() and valida:
            for fila in data.get('data'):
                student_module = self.get_or_create_student_module(fila[0])
                state = json.loads(student_module.state)
                score = int(fila[1])
                state['comment'] = fila[2]
                state['student_score'] = score
                student_module.state = json.dumps(state)
                student_module.save()

                from student.models import anonymous_id_for_user
                
                course_key = self.course_id
                anonymous_user_id = anonymous_id_for_user(User.objects.get(id=int(fila[0])), course_key)
                log.error(course_key)
                student_item = {
                    'student_id': anonymous_user_id,
                    'course_id': self.block_course_id,
                    'item_id': self.block_id,
                    'item_type': 'problem'
                }
                submission = self.get_submission(anonymous_user_id)
                if submission:
                    submissions_api.set_score(
                        submission['uuid'], score, self.puntajemax)
                else:
                    submission = submissions_api.create_submission(
                        student_item, 'any answer')
                    submissions_api.set_score(
                        submission['uuid'], score, self.puntajemax)

            return {
                'result': 'success',
                'id': '00',
                'n_student': len(
                    data.get('data'))}

        return {'result': 'error'}

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Called when submitting the form in Studio.
        """
        if data.get('puntajemax').lstrip(
                '+').isdigit() and int(data.get('puntajemax')) >= 0:
            self.display_name = data.get('display_name') or ""
            self.puntajemax = int(data.get('puntajemax')) or 100
            return {'result': 'success'}
        return {'result': 'error'}

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
