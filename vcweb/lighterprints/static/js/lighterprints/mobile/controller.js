var participant_group_id;
var plot1;
var globalViewModel;

//Model for details of the current activities used in home page and activity detail page 
/*
function LighterFootprintsModel(modelJson) {
    var self = this;
    var model = ko.mapping.fromJS(modelJson);
    // FIXME: hacky, figure out if there is a way to pass the observable in directly from the model object we get in
    // performActivity
    model.lastPerformedActivity = ko.observable();
    model.lastPerformedActivityPoints = ko.observable();
    model.errorMessage = ko.observable();
    model.hasChatMessages = function() {
        return model.chatMessages().length > 0;
    }
    
    model.submitChatMessage = function() {
    	var formData = "participant_group_id="+participant_group_id+"&"; 
        formData +=	$('#chat-form').serialize();
        $.post('http://vcweb.asu.edu/lighterprints/api/message', formData, function(data) {
                ko.mapping.fromJS(data, model);
                $('#groupPageMessageList').listview('refresh');
            });
        $('#chatText').val('');
        return false;
    };
    
    model.availableActivities = ko.computed(function() {
            return ko.utils.arrayFilter(model.activities(), function(activity) { return activity.available_now() });
    });
    
    model.availableL1 = ko.computed(function() {
        return ko.utils.arrayFilter(model.activities(), function(activity) {
        	console.log(activity.level());
        	if (activity.level() == '1') return true;
        });
    });
    
    model.availableL2 = ko.computed(function() {
        return ko.utils.arrayFilter(model.activities(), function(activity) {
        	console.log(activity.level());
        	if (activity.level() == '2') return true;
        });
    });
    
    model.availableL3 = ko.computed(function() {
        return ko.utils.arrayFilter(model.activities(), function(activity) {
        	console.log(activity.level());
        	if (activity.level() == '3') return true;
        });
    });
    
    model.hasAvailableActivities = ko.computed(function() {
            return model.availableActivities().length > 0;
    });
    return model;
}
*/

function initHomePageKO() {
	var homeUrl = "http://vcweb.asu.edu/lighterprints/api/view-model";
	var activity_id;
	var activity_name;
	$.ajax({
		type : "GET",
		url : homeUrl,
		data : {
			participant_group_id : participant_group_id
		},
		dataType : "json",
		cache : false,
		success : function(response) {
            var viewModelData = $.parseJSON(response.view_model_json);
            globalViewModel = new LighterFootprintsModel(viewModelData);
            globalViewModel.currentActivity = ko.observable();
            globalViewModel.showActivityDetail = function(activityModel) {
                globalViewModel.currentActivity(activityModel);
                activity_id = activityModel.pk;
                console.log("activity id and name");
                console.log(activity_id);
                activity_name = ko.utils.unwrapObservable(activityModel.display_name);
                console.log(activity_name);
                $.mobile.changePage("#activityDetailsPage");
            };
            globalViewModel.done = function() {
        		$.ajax({
        			type : 'POST',
        			url : "http://vcweb.asu.edu/lighterprints/api/do-activity",
        			data : {
        				participant_group_id : participant_group_id,
        				activity_id : activity_id,
        				latitude : "",
        				longitude : ""
        			},
        			dataType : "json",
        			success : function(data) {
        				if (data.success){
        					ko.mapping.fromJSON(data.viewModel, globalViewModel);
        					alert("Success:Performed Acitivity " + activity_name + "!");
        					//$.mobile.changePage('#popupDialog', "pop", false, false);	
        				}  
        				else
        					alert("Could not perform activity");
        				//initHomePageKO();
        				$.mobile.changePage('#homePage');
        			},
        			error : function(form, response) {
        				alert(response.message);
        			}
        		});
        	};
            
            ko.applyBindings(globalViewModel);
//            ko.applyBindings(globalViewModel, $('#homePage')[0]);
//            ko.applyBindings(globalViewModel, $('#homePage')[0]);
//            ko.applyBindings(globalViewModel, $('#homePage')[0]);
            
		},
		error : function(form, response) {
			alert(response.message);
		}
	});

};

function buildScorePage() {
	var groupScoreURL = "http://vcweb.asu.edu/lighterprints/api/group-score/"+participant_group_id;
	function parseResult(result) {
		console.debug("invoking parse data for group score");
		console.log(result);
		scoreObj = result.scores[0];
		console.log(scoreObj);
		var total_points = scoreObj.total_points;
		var points_to_next_level = scoreObj.points_to_next_level;
		var average_points_per_person = scoreObj.average_points_per_person;
		console.log(ko.utils.unwrapObservable(globalViewModel.groupLevel));
		// For horizontal bar charts, x an y values must will be "flipped"
		// from their vertical bar counterpart.
		plot1 = $.jqplot('scoreChart', [[points_to_next_level,total_points, average_points_per_person]],{
			title:'Group Level: '+ko.utils.unwrapObservable(globalViewModel.groupLevel),
			series:[{color:'#357EC7'}],
			seriesDefaults: {
				renderer:$.jqplot.BarRenderer,
				// Show point labels to the right ('e'ast) of each bar.
				// edgeTolerance of -15 allows labels flow outside the grid
				// up to 15 pixels. If they flow out more than that, they
				// will be hidden.
				//pointLabels: { show: true, location: 'e', edgeTolerance: -15 },
				pointLabels:{
			        show: true,
			        labels:['Average Needed To Advance', 'Total Group Points', 'Average Points Per Person'],
			        location: 'e', 
			        edgeTolerance: -100 
			      },
				// Rotate the bar shadow as if bar is lit from top right
				// Here's where we tell the chart it is oriented horizontally.
				rendererOptions: {
					barWidth: 20.0,
					barDirection: 'horizontal'
				}
			},
			axes: {
				xaxis:{max:1000},
				yaxis: {
					renderer: $.jqplot.CategoryAxisRenderer
				}
			}
		});
		plot1.replot({clear: true, resetAxes:true});
	}

	$.ajax({
		type : "GET",
		url : groupScoreURL,
		dataType : "json",
		cache : false,
		success : function(result) {
			$('scoreChart').empty();
			parseResult(result);
		},
		error : function(form, response) {
			alert(response.message);
		}
	});
};

$(document).live('pageinit', function(event) {	
	
	$("#submitLogin").click(function(event) {
		event.preventDefault();

		var formData = $("#loginForm").serialize();

		$.ajax({
			type : "POST",
			url : "http://vcweb.asu.edu/lighterprints/api/login",
			cache : false,
			data : formData,
			dataType : "json",
			success : function(data) {
				if (data.success == false) {
					alert("Invalid login!");
				} else if (data.success == true) {
					participant_group_id = data.participant_group_id;
					$.mobile.changePage($("#homePage"));
				}
			},
			error : function(form, response) {
				alert(response.message);
			}
		});
	});
	
		
	$("#loginPage").bind('pageinit', function(event) {
		participant_group_id ="";
	});
	$("#loginPage").bind('pageshow', function(event) {
		participant_group_id ="";
	});
	$("#homePage").bind('pageinit', function(event) {
		initHomePageKO();
		//initGroupPageKO();
	});

//	$("#homePage").bind('pageaftershow', function(event) {
//		//$("#homePageNoActFlag").listview('refresh');
//	});
	
	
	$('[data-role=page]').bind('pageshow', function(event) {
		if(participant_group_id == null){
				window.location.href="index.html";
	}
	});
	
	$('[data-role=page]').bind('pageinit', function(event) {
		if(participant_group_id == null){
				window.location.href="index.html";
	}
	});

	$("#activityDetailsPage").bind('pagebeforeshow', function(event) {
		$('#currActivityInfoList').listview('refresh');
		$('#currActivityDetailsList').listview('refresh');
		//$('#footerList').listview('refresh');
	});
	
	$("#messagePage").bind('pagebeforeshow', function(event) {
		$('#groupPageMessageList').listview('refresh');
	});
	
	$("#scorePage").bind('pageshow', function(event) {
		buildScorePage();
		$(window).resize(function() {
		      plot1.replot( { resetAxes: true } );
		});
	});

});
