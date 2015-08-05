.. Virtual Commons Web Environment documentation master file, created by
   sphinx-quickstart on Wed Aug  5 12:59:02 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The Virtual Commons Web Environment (vcweb)
===========================================================
The Virtual Commons Web Environment is a Django framework for developing collective action experiments. It provides a
flexible data model for experiment configuration and collecting data, real-time interactivity using `sockjs
<http://sockjs.org>`_ and `sockjs-tornado <https://github.com/mrjoes/sockjs-tornado>`_, integration with external survey
instruments like `Qualtrics <http://www.qualtrics.com>`_, participant management, and general scaffolding for
configuring and parameterizing group behavior experiments. Support for two broad classes of experiments are included:

    * *controlled experiments* conducted within a computer lab where an experimenter controls round transitions 
    * *long-running experiments*, e.g., one day corresponds to a single round and round transitions occur automatically
      at midnight

Several experiments have been implemented in vcweb:

* The Lighter Footprints experiment is a public good game where participants in different network and group structures
  perform virtual actions to reduce their carbon footprint. Development and analysis supported by NSF for the *Tipping
  Collective Action in Social Networks* project.
* The Boundary Effects experiment is a CPR resource experiment designed and run by Dr. Tim Waring, et al.
* Forestry, irrigation experiments as described in `Dynamics of Rules and Resources: Three New Field Experiments on
  Water, Forests, and Fisheries <http://commons.asu.edu/files/Cardenas_Janssen_Bousquet_Env_Exp_Econ_Handbook.pdf>`_ [DRR3]_


Contents:


.. toctree::
   :maxdepth: 2

   Getting started <getting-started>
   Developing new experiments <develop-new-experiments>
   VCWEB Core <core>
   Subject Pool Management <subjectpool>



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. [DRR3] Cardenas, J.C, M.A. Janssen, and F. Bousquet, Dynamics of Rules and Resources: Three New Field Experiments on Water, Forests and Fisheries, *Handbook on Experimental Economics and the Environment*, edited by John List and Michael Price (Edward Elgar Publishing)
