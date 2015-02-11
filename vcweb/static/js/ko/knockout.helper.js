//wrapper to an observable that requires accept/cancel
ko.protectedObservable = function(initialValue) {
    //private variables
    var _actualValue = ko.observable(initialValue),
        _tempValue = initialValue;

    //computed observable that we will return
    var result = ko.computed({
        //always return the actual value
        read: function() {
           return _actualValue();
        },
        //stored in a temporary spot until commit
        write: function(newValue) {
             _tempValue = newValue;
        }
    });

    //if different, commit temp value
    result.commit = function() {
        if (_tempValue !== _actualValue()) {
             _actualValue(_tempValue);
        }
    };

    //return updatedValue
    result.updateValue = function() {
        return _tempValue;
    };

    //force subscribers to take original
    result.reset = function() {
        _actualValue.valueHasMutated();
        _tempValue = _actualValue();   //reset temp value
    };

    return result;
};

ko.bindingHandlers.showModal = {
    update: function (element, valueAccessor) {
        var value = valueAccessor();
        if (ko.utils.unwrapObservable(value)) {
            $(element).modal('show');
            // this is to focus input field inside dialog
            $("input", element).focus();
            $('.has-popover', element).popover({'trigger':'hover'});
        }
        else {
            $(element).modal('hide');
        }
    }
};

ko.bindingHandlers.slideVisible = {
    init: function(element, valueAccessor) {
        // Initially set the element to be instantly visible/hidden depending on the value
        var value = valueAccessor();
        $(element).toggle(ko.unwrap(value)); // Use "unwrapObservable" so we can handle values that may or may not be observable
    },
    update: function(element, valueAccessor) {
        // Whenever the value subsequently changes, slowly fade the element in or out
        var value = valueAccessor();
        ko.unwrap(value) ? $(element).slideDown(200) : $(element).slideUp(200);
    }
};

ko.bindingHandlers.datetimepicker = {
    init: function(element, valueAccessor, allBindings) {
        //initialize datepicker with some optional options
        var options = {
            format: 'YYYY-MM-DD HH:mm',
            defaultDate: ko.unwrap(valueAccessor()),
            sideBySide: true,
        };
        ko.utils.extend(options, allBindings.dateTimePickerOptions);
        $(element).datetimepicker(options).on("dp.change", function (evntObj) {
            var observable = valueAccessor();
            if (evntObj.timeStamp !== undefined) {
                var picker = $(this).data("DateTimePicker");
                var d = picker.date();
                observable(d.format(options.format));
            }
        });
    },
    update: function (element, valueAccessor) {
        var value = ko.unwrap(valueAccessor());
        $(element).datetimepicker('date', value || '');
    }
};

ko.bindingHandlers.disableClick = {
    init: function (element, valueAccessor) {
        $(element).click(function(evt) {
            if(valueAccessor())
                evt.preventDefault();
        });
    },
    update: function(element, valueAccessor) {
        var value = ko.utils.unwrapObservable(valueAccessor());
        ko.bindingHandlers.css.update(element, function() {return { disabled: value }; });
    }
};
