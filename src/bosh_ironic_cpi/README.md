# BOSH Ironic CPI Release

This is *work in progress* to create BOSH release for the OpenStack Ironic CPI in
order to be able to manage physical servers using BOSH

See [Initializing a BOSH environment on OpenStack](https://bosh.io/docs/init-openstack.html)
for example usage.


## Ironic OpenStack

OpenStack is a collection of interrelated open source projects that, together, 
form a pluggable framework for building massively-scalable infrastructure as a 
service clouds. OpenStack represents the world's largest and fastest-growing 
open cloud community, a global collaboration of over 150 leading companies.

Ironic ...


## BOSH

BOSH is an open source tool chain for release engineering, deployment and 
lifecycle management of large scale distributed services. In this manual we 
describe the architecture, topology, configuration, and use of BOSH, as well 
as the structure and conventions used in packaging and deployment.

 * Documentation: [bosh.io/docs](https://bosh.io/docs)
 * BOSH Source Code: https://github.com/cloudfoundry/bosh


## Ironic ang BOSH working together

BOSH defines a Cloud Provider Interface API (CPI) which enables PaaS deployment 
across multiple cloud providers, initially VMWare's vSphere and AWS.

OpenStack Irnic CPI manages the deployment of a set of baremetal servers and 
enables applications to be deployed dynamically using BOSH. A common image, 
called a stem-cell, allows BOSH to build new physical machines enabling 
rapid scale-out.


## Author

Jose Riguera Lopez <jriguera@gmail.com>

