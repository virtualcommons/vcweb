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
        $.post('//lighterprints/api/perform-activity', formData, function(data){
            if (data.success) {
				console.debug(data);
                ko.mapping.fromJSON(data.viewModel, model);
				model.lastPerformedActivity(challengeModel);
				 $.mobile.changePage($("#modalPage"),{transition: 'pop', role: 'dialog'});
            }
            else {
                console.debug("ERROR: Unable to perform activity: " + data.message);
            }
        });
    };
		
    return model;
}

function initKOModel(response){
    var groupURL = "//lighterprints/api/view-model/" + participant_group_id;
    $.get({
        url: groupURL,
        dataType: "json",
        cache: false,
        success: function(response){
            var viewModelData = $.parseJSON(response.viewModel);
            globalViewModel = new LighterFootprintsModel(viewModelData);
			ko.applyBindings(globalViewModel);
			$.mobile.changePage($("#dashboardPage"));
        },
        error: function(form, response){
            alert(response.message);
        }
    });
}

$(document).live('pageinit', function(event){
	
    $("#submitLogin").click(function(event){
        event.preventDefault();
        
        var formData = $("#loginForm").serialize();
        $.ajax({
            type: "POST",
            url: "//lighterprints/api/login",
            cache: false,
            data: formData,
            dataType: "json",
            success: function(data){
                if (data.success == false) {
                    alert("Invalid login!");
                }
                else 
                    if (data.success == true) {
						participant_group_id = data.participant_group_id;						
                        initKOModel();
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
        $.post('//lighterprints/api/message', formData, function(response) {
                if (response.success) {
                    console.debug("successful post - updated view model: ");
                    ko.mapping.fromJS(response.viewModel, globalViewModel);
					$('#chatMessageList').listview('refresh');
                }
                else {
                    console.debug("unable to post message to server");
                    console.debug(response);
                }
            });
        $('#chatText').val('');
    });
	$("#dashboardPage").bind('pageaftershow', function(event) {
		$('#challengesList').listview('refresh');
		//$('#challengesNavbarList').listview('refresh');
	});
});

