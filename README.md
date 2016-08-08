# bosh-ironic-cpi

A Bosh CPI to manage baremetal servers using Ironic (Standalone).

Tested using https://github.com/jriguera/ansible-ironic-standalone

**WORK in PROGRESS**


Some "screenshots":
```
$ bosh status
Config
             /home/jriguera/.bosh_config

Director
  Name       ironic-bosh
  URL        https://10.230.0.31:25555
  Version    1.3232.2.0 (00000000)
  User       admin
  UUID       1c9788b5-46c9-4a11-bc15-9963c438dfb5
  CPI        ironic_cpi
  dns        disabled
  compiled_package_cache disabled
  snapshots  disabled

Deployment
  not set

```

BOSH view:

```
$ bosh vms
https://10.230.0.31:25555
Acting as user 'admin' on 'ironic-bosh'
Deployment 'carbon-c-relay'

Director task 25119

Task 25119 done

+-----------------------------------------------+---------+----+----------+---------------+
| VM                                            | State   | AZ | VM Type  | IPs           |
+-----------------------------------------------+---------+----+----------+---------------+
| test/0 (440565a8-e9ae-4805-8674-679d04471b13) | running | z1 | default  | 10.230.44.250 |
+-----------------------------------------------+---------+---------------+---------------+

VMs total: 1

```

Ironic view:

```
$ ironic node-list
+--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+
| UUID                                 | Name   | Instance UUID                        | Power State | Provisioning State | Maintenance |
+--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+
| 4c537b00-72ff-4350-84f0-f3e957ec1bf8 | test-0 | 440565a8-e9ae-4805-8674-679d04471b13 | power on    | active             | False       |
| 666e20fe-4681-411e-85c9-21d615171714 | None   | None                                 | None        | enroll             | False       |
+--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+

```

This BOSH Release has two jobs. **ironic_cpi**, the main one, the implementation of the CPI 
and an optional **dav_registry** which is an implementation of the BOSH Registry API in Lua 
for Nginx. Making the most of the WebDAV protocol (which is needed to manage the Config-Drive 
Metatata for Ironic standalone) I have decided to create a simple implementation of the Registry
API to delegate in WebDAV as bakend. The JSON *settings* needed by the agent is really simple, 
no database is needed, it is possible to use the Config-Drive Metadata as storage. The Lua 
implementation just does internal redirections to metadata location, doing some checks and 
creating the JSON file. There are two ideas behing this implementation:

  * To run this program in a external NGINX server, the one which provides the ConfigDrive Metadata. 
  Ironic ConfigDrive Metadata and Stemcells can be living on the same location as the registry,
  centralizing all BOSH Agent specifications for every server on the same repository.
  
  * Run the WebDAV inside BOSH VM providing Stemcell and ConfigDrive Metadata storage and 
  Registry API.


# General considerations

Before running this sofware, take into account:


* Servers must be predefined on Ironic (as *enroll* state) or defined using the **ironic_params**
properties. When the CPI runs, depending on the configuration, it wil take one of the available
servers in *enroll* (by searching by MAC or by hardware specs: memory, cpu, disk ...) or it
will define the baremetal server in Ironic by itself.

* Baremetal servers need at least two disks. Because of how Bosh Agent works and how Ironic sets 
up the ConfigDrive as a small partition at the end of the first device (*/dev/sda*), Bosh Agent 
is not able to manage partitions on such way on the first device, as consecuence, a second 
device (*/dev/sdb*) is needed for ephemeral data. A 3rd device would be used for persistent data.

* The CPI can deploy normal OpenStack stemcells. They work on most of the hardware, but take into 
account there are some NICs or storage devices which would need aditional drivers. In that case, 
you will need to build your own stemcell including those drivers.

* A physical server usually has several NICs available, but maybe some of them are not connected 
or needed. When BOSH Agent runs, it ensures all the interfaces defined on the server must have an IP,
if an NIC has no IP address, Bosh Agent fails. To hack this limitation I have decided to assign 
an IP on the loopback range 127.0.0.100/24 to the non used interfaces. That is why all the MAC 
addresses must be defined (or discovered) in Ironic, to create such static network definitions.

* Bonding is needed!. In the VM world it does not make sense, but in the physical worl most of
the times is desirable (unless there are a lot of servers and by defining aggregations one 
can assume losing some of them). In order to provide bonding, stemcells must be created with
the proper settings and BOSH agent functionality should be changed. A similar issues appears
if one needs to define VLANS (besides the option of having OpenStack Neutron controlling the
switch ports) for some NIC(s).

* LVM and/or RAID not supported. LVM would be nice, but I think it will require a lot of 
changes in BOSH Agent. RAID setup could be managed by Ironic.



# Motivations

* Hack "Day" project just for learn and to make most of Ansible Ironic project, in order to 
define a common standard way to manage physical servers.

* Python? Why not? Is a great language which does not need to be compiled and (the main reason) 
OpenStack is made with it, so the libraries provide all the functionality. Also, the Ironic 
library provides functions to create ConfigDrive(s).

* One of the first ideas was about creating a smart CPI. OpenStack Nova provides an API to 
deploy servers (baremetal or VM). This could be a different approach to have a CPI able to 
deploy VMs and physical servers using the same BOSH Director. One could have VMware for VMs 
and Ironic for special jobs like Cloud Foundry runners. The CPI would delegate the calls on
the other one for VM management. I am not sure if this is really needed ...


# Local Dev environment

Run `bosh_prepare` to download the sources.
