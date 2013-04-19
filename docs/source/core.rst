VCWEB Core
==========

The vcweb core app provides data models and support for experiments, configurations,
participants, experimenters, and three primary types of data:

 1. participant data generated during the course of a round
 2. group data shared across each participant in the group
 3. round and experiment configuration parameterizations

Using the forestry experiment as a concrete example, participant data consists of a harvest decision in a given round or
a chat message.  Group shared data consists of the current resource level for a given group and the amount of regrowth
experienced by the group.  Round and experiment configuration parameterization data includes how many initial trees are
provided at the start of the experiment, the regrowth rate, the number of rounds, etc.

.. automodule:: vcweb.core.models
        :members:
