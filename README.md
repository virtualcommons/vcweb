### vcweb 
vcweb is a Python/Django framework that purportedly helps when building interactive web-based experiments for collective action researchers interested in social ecological systems.

### features
* web based experiment and round parameterization of experiments that can be cloned, exported, and modified
* support for controlled experiments, timed rounds with parameterizable duration, and round transitions manually
  managed by an experiment facilitator (with active development to implement automated round transitions)
* support for extended experiments spanning multiple days or weeks with cron-based scheduled custom experiment
  logic (e.g., at midnight perform some calculations, determine current state of a resource and payments and send a
  summary email to the registered participants)
* flexible data model that captures Experiments, ExperimentConfigurations, RoundConfigurations, and arbitrary experiment
  data via the [Entity Attribute Value Model](http://en.wikipedia.org/wiki/Entity%E2%80%93attribute%E2%80%93value_model)
  to capture participant data and group data. Work is ongoing to simplify and improve this API.
* real-time chat and server push via [sockjs-tornado](https://github.com/mrjoes/sockjs-tornado)
* current experiment UIs are implemented using [Bootstrap 3](http://getbootstrap.com) and [knockout](http://knockoutjs.com) but the
view layer is unopinionated and experiments can implement any browser based UI. Try
[reactjs](http://facebook.github.io/react/) and [Om](https://github.com/swannodette/om),
[angular](https://angularjs.org/), [emberjs](http://emberjs.com/), javascript / canvas libraries like
[d3js](http://d3js.org/) or [processingjs](http://ejohn.org/blog/processingjs/).
You'll still have to deal with Python/Django on the server side though.

### run an experiment

In order to run a vcweb experiment you'll need an experimenter account. Please [contact us](http://vcweb.asu.edu/contact)
if you'd like to request an experimenter account. 

### participate in an experiment

In order to participate in a vcweb experiment you must be invited to one by an experimenter. 

### develop an experiment or contribute to the infrastructure

For more information on how to install and deploy the software please visit <https://bitbucket.org/virtualcommons/vcweb/wiki/Home>
