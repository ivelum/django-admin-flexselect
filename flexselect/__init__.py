from itertools import chain
import json

from django import VERSION as DJANGO_VERSION

from django.apps import apps
if DJANGO_VERSION < (2, 0, 0):
    from django.core.urlresolvers import reverse, resolve
else:
    from django.urls import reverse, resolve

from django.forms.widgets import Select, SelectMultiple
if DJANGO_VERSION < (4, 0, 0):
    from django.utils.encoding import smart_text as smart_unicode
else:
    from django.utils.encoding import smart_str as smart_unicode
from django.utils.safestring import mark_safe
from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist

EMPTY_CHOICE = ('', '---------')

# Update default settings.
FLEXSELECT = {
    'include_jquery': False,
}

try:
    FLEXSELECT.update(settings.FLEXSELECT)
except AttributeError:
    pass


def choices_from_queryset(queryset):
    """
    Makes choices from a QuerySet in a format that is usable by the
    django.forms.widget.Select widget.

    queryset: An instance of django.db.models.query.QuerySet
    """
    return chain(
        [EMPTY_CHOICE],
        [(o.pk, smart_unicode(o)) for o in queryset],
    )


def choices_from_instance(instance, widget):
    """
    Builds choices from a model instance using the widgets queryset() method.
    If any of the widgets trigger_field fields is not defined on the instance
    or the instance itself is None, None is returned.

    instance: An instance of the model used on the current admin page.
    widget: A widget instance given to the FlexSelectWidget.
    """
    try:
        for trigger_field in widget.trigger_fields:
            getattr(instance, trigger_field)
    except (ObjectDoesNotExist, AttributeError):
        return [('', widget.empty_choices_text(instance))]

    return choices_from_queryset(widget.queryset(instance))


def details_from_instance(instance, widget):
    """
    Builds html from a model instance using the widgets details() method. If
    any of the widgets trigger_field fields is not defined on the instance or
    the instance itself is None, None is returned.

    instance: An instance of the model used on the current admin page.
    widget: A widget instance given to the FlexSelectWidget.
    """
    try:
        for trigger_field in widget.trigger_fields:
            getattr(instance, trigger_field)
        related_instance = getattr(instance, widget.base_field.name)
    except (ObjectDoesNotExist, AttributeError):
        return u''
    return widget.details(related_instance, instance)


def object_from_request(request):
    try:
        if DJANGO_VERSION < (2, 0, 0):
            object_pk = resolve(request.path).args[0]
        else:
            object_pk = resolve(request.path).kwargs['object_id']
    except (IndexError, KeyError):
        raise ValueError(request.path)
    return model_from_request(request).objects.get(pk=object_pk)


def model_from_request(request):
    resolved = resolve(request.path)
    url_parts = resolved.url_name.split('_')
    app_name = model_name = ''
    for app in apps.app_configs.keys():
        app_parts = app.split('_')
        if app_parts == url_parts[:len(app_parts)]:
            app_name = app
            for m in apps.app_configs[app].models.keys():
                if m == url_parts[len(app_parts)]:
                    model_name = url_parts[len(app_parts)]
                    break
    if not (app_name and model_name):
        raise ValueError(
            f'Cannot resolve model name from request: {resolved.url_name}.',
        )
    return apps.get_model(app_label=app_name, model_name=model_name)


class FlexBaseWidget(object):
    class Media:
        js = []
        if FLEXSELECT['include_jquery']:
            googlecdn = "https://ajax.googleapis.com/ajax/libs"
            js.append('%s/jquery/1.6.1/jquery.min.js' % googlecdn)
            js.append('%s/jqueryui/1.8.13/jquery-ui.min.js' % googlecdn)
        # Load RelatedObjectLookups.js before flexselect.js
        js.append('admin/js/admin/RelatedObjectLookups.js')
        js.append('flexselect/js/flexselect.js')

    def __init__(self, base_field, modeladmin, request, choice_function=None,
                 *args, **kwargs):
        self.choice_function = choice_function
        self.base_field = base_field
        self.modeladmin = modeladmin
        self.request = request
        super(FlexBaseWidget, self).__init__(*args, **kwargs)

    @classmethod
    def object_from_post(cls, model, data):
        """
        Returns a partial instance of the widgets model loading it with values
        from a POST request.
        """
        items = dict(data.items())
        values = {}
        for f in model._meta.fields:
            if f.name in items:
                try:
                    value = f.formfield().to_python(items[f.name])
                    if value is not None:
                        values[f.name] = value
                except ValidationError:
                    pass
        return model(**values)

    def get_unique_name(self):
        return '__'.join((
            self.modeladmin.model._meta.app_label,
            self.modeladmin.model.__name__,
            self.base_field.name,
        )).lower()

    def _get_model_instance(self):
        """
        Returns a model instance from the url in the admin page.
        """
        if 'hashed_name' in self.request.POST:
            hashed_name = self.request.POST.get('hashed_name')
            model = apps.get_model(*hashed_name.split('__')[:2])
            obj = self.object_from_post(model, self.request.POST)
        else:
            try:
                obj = object_from_request(self.request)
            except ValueError:
                model = model_from_request(self.request)
                obj = self.object_from_post(model, self.request.POST)
        return obj

    def _build_js(self):
        """
        Adds the widgets hashed_name as the key with an array of its
        trigger_fields as the value to flexselect.selects.
        """
        return """
        <script>
            var flexselect = flexselect || {};
            flexselect.fields = flexselect.fields || {};
            flexselect.fields.%s = %s;
        </script>""" % (
            self.get_unique_name(),
            json.dumps({
                'baseField': self.base_field.name,
                'triggerFields': self.trigger_fields,
                'url': reverse('flexselect_field_changed'),
            }),
        )

    def render(self, name, value, attrs=None, choices=(), *args, **kwargs):
        """
        Overrides. Reduces the choices by calling the widgets queryset()
        method and adds a details <span> that is filled with the widgets
        details() method.
        """
        instance = self._get_model_instance()
        if self.choice_function:
            self.choices = self.choice_function(instance)
        else:
            self.choices = choices_from_instance(instance, self)
        return mark_safe(''.join([
            super(FlexBaseWidget, self).render(
                name, value, attrs=attrs,
                *args, **kwargs
            ),
            self._build_js(),
            '<span class="flexselect_details">',
            details_from_instance(instance, self),
            '</span>',
        ]))

    # Methods and properties that must be implemented.

    trigger_fields = []

    def details(self, base_field_instance, instance):
        raise NotImplementedError

    def queryset(self, instance):
        raise NotImplementedError

    def empty_choices_text(self, instance):
        raise NotImplementedError


class FlexSelectWidget(FlexBaseWidget, Select):
    template_name = 'admin/flexselect/flexselect.html'
    optiongroup_template_name = 'admin/flexselect/flexselect_optgroups.html'

    def render_options_template(self, selected_items, attrs):
        # django 1.11 only
        context = self.get_context(
            self.base_field.name,
            selected_items,
            attrs=attrs,
        )
        return self._render(self.optiongroup_template_name, context)


class FlexSelectMultipleWidget(FlexBaseWidget, SelectMultiple):
    def __init__(self, *args, **kwargs):
        super(FlexSelectMultipleWidget, self).__init__(*args, **kwargs)
