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
            $('.has-popover').popover({'trigger':'hover'});
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


ko.bindingHandlers.datepicker = {
    init: function(element, valueAccessor, allBindingsAccessor) {
        //initialize datepicker with some optional options
        var options = { format: 'yyyy-mm-dd', start_date: '-d' };
        $(element).datepicker(options);

        //when a user changes the date, update the view model
        ko.utils.registerEventHandler(element, "changeDate", function(event) {
            var value = valueAccessor();
            if (ko.isObservable(value) && event.date > new Date()) {
                value(event.date);
            }
        });
    },
    update: function(element, valueAccessor)   {
        var widget = $(element).data("datepicker");
        //when the view model is updated, update the widget
        if (widget) {
            widget.date = new Date(ko.utils.unwrapObservable(valueAccessor()));
            widget.setValue();
        }
        $('.datepicker').hide();
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

