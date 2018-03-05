import json

from django.http import HttpResponse
from django.forms.widgets import Select
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.contrib import admin
from django import VERSION as DJANGO_VERSION

from flexselect import (FlexSelectWidget, choices_from_instance,
                        details_from_instance)


@login_required
def field_changed(request):
    """
    Ajax callback called when a trigger field or base field has changed.
    Returns html for new options and details for the dependent field as json.
    """
    hashed_name = request.POST.get('hashed_name')
    app_label, model_name, base_field_name = hashed_name.split('__')
    model = apps.get_model(app_label, model_name)
    obj = FlexSelectWidget.object_from_post(model, request.POST)
    value_fk = getattr(obj, base_field_name, None)
    admin_instance = admin.site._registry[obj.__class__]
    base_field = next(f for f in obj._meta.fields if f.name == base_field_name)
    widget = admin_instance.formfield_for_dbfield(
        base_field,
        request=request,
    ).widget.widget

    if bool(int(request.POST['include_options'])):
        if widget.choice_function:
            choices = widget.choice_function(obj)
        else:
            choices = choices_from_instance(obj, widget)

        args = [[value_fk.pk if value_fk else None]]
        if DJANGO_VERSION < (1, 10, 0):
            args.insert(0, [])
        if DJANGO_VERSION < (1, 11, 0):
            options = Select(choices=choices).render_options(*args)
        else:
            # django 1.11 has introduced template rednering for widgets
            widget.choices = choices
            val = value_fk.pk if value_fk else None
            options = widget.render_options_template(val, widget.attrs)
    else:
        options = None

    return HttpResponse(json.dumps({
        'options': options,
        'details': details_from_instance(obj, widget),
    }), content_type='application/json')
