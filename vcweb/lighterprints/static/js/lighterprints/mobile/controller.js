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
	
	model.perform = function(challengeModel){
        if (!challengeModel.availableNow()) {
            console.debug("tried to perform an activity that's not available right now");
            console.debug(challengeModel);
            return;
        }
        var id = challengeModel.pk();
        var formData = $('#challengeForm' + id).serialize();
        $.post('http://vcweb.asu.edu/lighterprints/api/do-activity', formData, function(data){
            if (data.success) {
				console.debug(data);
                ko.mapping.fromJSON(data.viewModel, model);
				model.lastPerformedActivity(challengeModel);
				 $.mobile.changePage($("#modalPage"),{transition: 'pop', role: 'dialog'});
            }
            else {
                console.debug("ERROR: " + data.message);
                globalViewModel.errorMessage("Unable to perform activity: " + data.message);
                $('#activityUnavailableModal').modal();
            }
        });
    };
		
    return model;
}