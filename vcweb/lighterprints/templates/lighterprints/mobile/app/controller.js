var participant_group_id = '';
var globalViewModel;

function LighterFootprintsModel(modelJson){
    var self = this;
    var model = ko.mapping.fromJS(modelJson);
    model.hasGroupActivity = ko.computed(function(){
        return model.groupActivity().length > 0;
    });
	model.groupActivityTemplate = function(groupActivity) {
        return groupActivity.parameter_name();
    };
	model.teamActivity = ko.computed(function() {
        return ko.utils.arrayFilter(model.groupActivity(), function(groupActivity) {
            return groupActivity.parameter_name().indexOf("chat_message") != 0;
        });
    });
	model.chatMessages = ko.computed(function() {
            return ko.utils.arrayFilter(model.groupActivity(), function(groupActivity) { return groupActivity.parameter_name().indexOf("chat_message") === 0 });
        });
    model.hasChatMessages = ko.computed(function() {
        return model.chatMessages().length > 0;
    });
    model.lockedChallenges = ko.computed(function(){
        return ko.utils.arrayFilter(model.activities(), function(activity){
            return activity.locked()
        });
    });
    model.unlockedChallenges = ko.computed(function(){
        return ko.utils.arrayFilter(model.activities(), function(activity){
            return !activity.locked()
        });
    });
    model.availableActivities = ko.computed(function(){
        return ko.utils.arrayFilter(model.activities(), function(activity){
            return activity.availableNow()
        });
    });
    model.hasAvailableActivities = ko.computed(function(){
        return model.availableActivities().length > 0;
    });
	model.lastPerformedActivity = ko.observable();
		
    return model;
}

function initKOModel(response){
    var viewModelData = $.parseJSON(response.view_model_json);
    globalViewModel = new LighterFootprintsModel(viewModelData);
    // custom view model methods, some of these may be lifted into the model itself
    globalViewModel.perform = function(challengeModel){
        if (!challengeModel.availableNow()) {
            console.debug("tried to perform an activity that's not available right now");
            console.debug(challengeModel);
            return;
        }
        var id = challengeModel.pk();
        var formData = $('#challengeForm' + id).serialize();
        $.post('http://vcweb.asu.edu/lighterprints/api/do-activity', formData, function(data){
            if (data.success) {
                ko.mapping.fromJSON(data.globalViewModel, globalViewModel);
				globalViewModel.lastPerformedActivity(challengeModel);
				 $.mobile.changePage($("#modalPage"),{transition: 'pop', role: 'dialog'});
            }
            else {
                console.debug("ERROR: " + data.message);
                globalViewModel.errorMessage("Unable to perform activity: " + data.message);
                $('#activityUnavailableModal').modal();
            }
        });
    };
    
    ko.applyBindings(globalViewModel);
    
}

$(document).live('pageinit', function(event){
	
    $("#submitLogin").click(function(event){
        event.preventDefault();
        
        var formData = $("#loginForm").serialize();
        $.ajax({
            type: "POST",
            url: "http://vcweb.asu.edu/lighterprints/api/view-model/1005",
            cache: false,
            data: formData,
            dataType: "json",
            success: function(data){
                if (data.success == false) {
                    alert("Invalid login!");
                }
                else 
                    if (data.success == true) {
                        initKOModel(data);
						console.debug(data);
                        $.mobile.changePage($("#dashboardPage"));
                    }
            },
            error: function(form, response){
                alert(response.message);
            }
        });
    });
	
	 $("#submitChatMessage").click(function(event){
        event.preventDefault();

        var formData = $('#chat-form').serialize();
        $.post('https://vcweb.asu.edu/lighterprints/api/message', formData, function(response) {
                if (response.success) {
                    console.debug("successful post - updated view model: ");
                    ko.mapping.fromJS(response.viewModel, globalViewModel);
                }
                else {
                    console.debug("unable to post message to server");
                    console.debug(response);
                }
            });
        $('#chatText').val('');
        return false;
    });
    
});
