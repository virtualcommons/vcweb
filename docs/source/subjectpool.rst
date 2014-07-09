VCWEB Subject Pool
==========

The vcweb subject pool app handles participant invitations and signups. It allows experimenters to create and manage
experiment sessions and send randomized invitations out to participants in the subject pool who have opted in.
Important thing to note about this app is that it is accessible by only experimenters (users having experimenter privilege).

The vcweb subject pool app enables experimenters to see active as well as past experiment sessions.

Tha subject pool app provides following functionality to the experimenter

**Create or Modify an Experiment Session**

- On the active sessions tab experimenter can find a add session button. By clicking on that it the app will create an experiment session with default values. Experimenter can modify those details and finally click save button to create the session. The things to remember while creating the experiment session is that the experiment session time are in 24HR format.
- After saving the Experiment session if want to modify experiment session details you can click on the edit button beside the save button and all the fields of the experiment session will become editable so that you can make changes.

**Invite Participants**

- To invite participants for a series of experiment session, experimenter can click on the checkboxes beside each experiment session for which he/her want to send out invites.
- After Selecting the experiment sessions click on the invite button to open up the invitation form. The invite button would not be enabled if you haven't selected any experiment sessions.
- Fill up the invitation form and click on preview button to see the preview of the email that will be sent to the participants.

**Calendar**

- Experimenter can visualize the sessions of the all the experiments that are active as well as completed on the calendar.
- Experimenter have the option to see the calendar Year, Month, Week and day wise.
- Experimenter can also see the experiment session details by clicking on the experiment session name on the calendar

.. automodule:: vcweb.core.subjectpool
        :members:
