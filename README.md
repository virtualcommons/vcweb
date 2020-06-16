### vcweb 
vcweb is a Python/Django framework for developing collective action experiments. These experiments are characterized by
parameterizable experiment configurations with parameters applicable across the entire experiment or specific to a given
round and a random set of participants that are partitioned into groups (or networks). Our experiments typically
involve common pool resources where individuals must balance self interest with the good of the group or linear public
good games where majority group contribution is needed to maximize payoffs.

We maintain a managed instance of vcweb at https://commons.asu.edu but you are welcome to host your own server.

### features

* Subject pool management: participant recruitment and experiment session management with custom invitation emails
* Real-time chat and server push events via [sockjs-tornado](https://github.com/mrjoes/sockjs-tornado) and Redis
* Support for two broad classes of experiments:
    - Controlled experiments typically run in a computer lab with captive participants, characterized by timed rounds of
      parameterizable duration, and round transitions manually managed by an experiment facilitator, i.e., when all
      participants have completed a round or the round duration has expired, the experiment facilitator is notified in
      their web interface that time is up and that they can safely advance to the next round. When they click the
      "Advance to next round" button, all participants are automatically transitioned to the next round. Development is
      ongoing to properly implement automated round transitions where all participants automatically advance to the next
      round when user input is finished.
    - Extended experiments that span multiple days or weeks with scheduled custom experiment logic, e.g., at midnight
      determine the current state of a resource and up-till-now payments, then send summary emails to all registered
      participants.
* Web based experiment parameterization for multiple treatments with support for experiment-wide and round-specific
  parameters. Standard parameters include show up fees, exchange rate for tokens to currency, round durations, and group size.
  Custom parameters are defined by experiment developers; examples include initial resource levels and regrowth factors
  for a common pool resource game. An experiment treatment consists of an ordered set of round parameterizations. Round
  parameterizations can be specified to repeat N times as well.
* Flexible data model for managing the metadata and relationships between Experiments, ExperimentConfigurations,
  RoundConfigurations, and generated Participant and Group data. Work is ongoing to simplify and improve this API.
* Existing experiment UIs have been implemented using [Bootstrap 3](http://getbootstrap.com), 
  [knockout](http://knockoutjs.com), [jQuery Mobile](http://jquerymobile.com), and [Sencha Touch](http://www.sencha.com)
  but the view layer is unopinionated and experiments can be implemented with arbitrary web or mobile UIs. Some ideas:
  [reactjs](http://facebook.github.io/react/) and [Om](https://github.com/swannodette/om),
  [angular](https://angularjs.org/), [emberjs](http://emberjs.com/), 
  [d3js](http://d3js.org/), [processingjs](http://ejohn.org/blog/processingjs/). 


### run experiments or develop new experiments

Please [contact us](http://commons.asu.edu/contact) if you'd like to request an experimenter account or develop new
experiments

### participate in an experiment

In order to participate in a commons experiment you must be invited to one by an experimenter. 

### try it out

You can try the software as a demo experimenter by logging in to https://commons.asu.edu with the following credentials:

* Email: vcweb@mailinator.com
* Password: demo

This experimenter has limited access to a single experiment, a Forestry Communication / No Communication setup. You can
view the page by clicking on the "Monitor" button to connect to the experiment and view any generated data. There are
10 demo participants registered with the experiment. Their credentials are listed below

* Email: s1asu@mailinator.com, s2asu@mailinator.com, ..., s10asu@mailinator.com
* Password: test 

### codebase status
[![Build Status](https://travis-ci.org/virtualcommons/vcweb.svg?branch=master)](https://travis-ci.org/virtualcommons/vcweb)
[![Coverage Status](https://coveralls.io/repos/virtualcommons/vcweb/badge.png?branch=master)](https://coveralls.io/r/virtualcommons/vcweb?branch=develop)
