(function($, that) {

  // Namespace.
  var flexselect = flexselect || {};

  /**
   * Binds base and trigger fields.
   */
  flexselect.bindEvents = function() {
    if (typeof that.flexselect === 'undefined') return;
    var fields = that.flexselect.fields;
    $.each(fields, function(hashedName, field) {
      flexselect.bindBaseField(field.baseField, hashedName, field.url);
      $.each(field.triggerFields, function(key, triggerField) {
        flexselect.bindTriggerField(triggerField, hashedName,
                                    field.baseField, field.url);
      });
    });
  };

  /**
   * Binds the change event of a base field to the flexselect.ajax() function.
   */
  flexselect.bindBaseField = function(baseField, hashedName, url) {
    var data = {
      baseField: baseField,
      hashedName: hashedName,
      url: url,
      success: function(data) {
        $(this).parent().find('span.flexselect_details').html(data.details);
      },
      data: '&include_options=0'
    };
    flexselect.getElement(baseField)
      .on('change', data, flexselect.ajax)
      .trigger('change');
  };

  /**
   * Binds the change event of a trigger field to the flexselect.ajax() function.
   */
  flexselect.bindTriggerField = function(triggerField, hashedName,
                                         baseField, url) {
    var data = {
      baseField: baseField,
      hashedName: hashedName,
      url: url,
      success: function(data) {
        $(this).html(data.options);
        $(this).parent().find('span.flexselect_details').html('');
        // If jQueryUI is installed, flash the dependent form field row.
        if (typeof $.ui !== 'undefined') {
          $(this).parents('.form-row')
              .stop()
              .css('background-color', '#F49207')
              .animate({backgroundColor: 'white'}, 4000);
        }
      },
      data: '&include_options=1'
    };
    flexselect.getElement(triggerField).on('change', data, flexselect.ajax);
  };

  /**
   * Performs a ajax call that options the base field. In the event.data it needs
   * the keys "hashedName", "baseField", "data" and "success".
   */
  flexselect.ajax = function(event) {
    $.ajax({
      url: event.data.url,
      data: $('form').serialize() + '&hashed_name=' + event.data.hashedName
          + event.data.data,
      type: 'post',
      context: flexselect.getElement(event.data.baseField),
      success: event.data.success,
      error: function(data) {
        window.alert("Something went wrong with flexselect.");
      }
    });
  };

  /**
   * Returns the form element from a field name in the model.
   */
  flexselect.getElement = function(fieldName) {
    return $('#id_' + fieldName);
  };

  /**
   * Moves all details fields to after the green plussign.
   */
  flexselect.moveAfterPlussign = function() {
    // Delay execution to after all other initial js have been run.
    window.setTimeout(function() {
      $('span.flexselect_details').each(function() {
        $(this).next('.add-another').after($(this));
      });
    }, 1);
  };

  /**
   * Overrides the original dismissAddAnotherPopup and triggers a change event on
   * the field after the popup has been added.
   */
  var _dismissAddAnotherPopup = window.dismissAddAnotherPopup;

  window.dismissAddAnotherPopup = function(win, newId, newRepr) {
    _dismissAddAnotherPopup(win, newId, newRepr);
    $('#' + window.windowname_to_id(win.name)).trigger('change');
  };
  window.dismissAddAnotherPopup.original = _dismissAddAnotherPopup;

  // On Document.ready().
  $(function() {
    flexselect.bindEvents();
    flexselect.moveAfterPlussign();
  });

})(jQuery || django.jQuery, this);
