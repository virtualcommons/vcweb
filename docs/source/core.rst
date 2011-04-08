VCWEB Core
==========

The vcweb core app provides data models and support for experiments, configurations,
participants, experimenters, and three primary types of data:

 1. participant data generated during the course of a round
 2. group data shared across each participant in the group
 3. round and experiment configuration data.

Using the forestry experiment as a concrete example, participant data may consist of
a harvest decision in a given round or a chat message sent during a communication
round.  Examples of group shared data are the current resource level for a given
group and the amount of regrowth experienced by the group.  Round and experiment
configuration data include how many initial trees are provided at the start of the
experiment, how many rounds the experiment should consist of as well as the explicit
ordering of the rounds.

.. automodule:: vcweb.core.models
        :members:
