# bosh-ironic-cpi

A Bosh CPI (Cloud Provider Interface) to manage baremetal servers via Ironic 
(Standalone mode, without the rest of OpenStack components). The idea is make 
the most of OpenStack Ironic to provide an alternative way to deploy physical 
servers with BOSH. If you do not know about how amazing is BOSH, have a look 
here: http://bosh.io/

Tested using https://github.com/jriguera/ansible-ironic-standalone but it should
work with any Ironic installation.


Some *screenshots* about the project:

```
$ bosh status
Config
             /home/jriguera/.bosh_config

Director
  Name       ironic-bosh
  URL        https://10.100.0.1:25555
  Version    1.3262.9.0 (00000000)
  User       admin
  UUID       1c9788b5-46c9-4a11-bc15-9963c438dfb5
  CPI        ironic_cpi
  dns        disabled
  compiled_package_cache disabled
  snapshots  disabled

Deployment
  not set
```

BOSH perspective:

```
$ bosh instances
https://10.230.0.31:25555
Acting as user 'admin' on deployment 'carbon-c-relay' on 'ironic-bosh'

Director task 25720

Task 25720 done

+------------------------------------------------+---------+------+---------+---------------+
| Instance                                       | State   | AZ   | VM Type | IPs           |
+------------------------------------------------+---------+------+---------+---------------+
| test/0 (e633088f-11a9-4ee6-b26f-2388f29d2d1d)* | running | dogo | pool-01 | 10.0.0.3      |
+------------------------------------------------+---------+------+---------+---------------+

(*) Bootstrap node

Instances total: 1
```

Ironic point of view of the instances:

```
$ ironic node-list
+--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+
| UUID                                 | Name   | Instance UUID                        | Power State | Provisioning State | Maintenance |
+--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+
| 666e20fe-4681-411e-85c9-21d615171714 | None   | None                                 | None        | enroll             | False       |
| 87f8401e-9f13-4afc-b015-bf75738b44b6 | None   | None                                 | None        | enroll             | False       |
| 05c389e8-70d4-4473-941a-d5cde6b05558 | None   | None                                 | None        | enroll             | False       |
| a1b555ed-9555-4a74-a091-c5cd00b58ed1 | None   | None                                 | power off   | available          | False       |
| db7f1933-d375-458d-b77e-75dee63a85ef | lab1   | None                                 | power off   | manageable         | False       |
| 4e5d7a7b-75e6-4d3e-bec8-38a047fdab18 | test-0 | e633088f-11a9-4ee6-b26f-2388f29d2d1d | power on    | active             | False       |
+--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+

```


# Motivations

* Hack "Day" (actually months) project to learn about BOSH internals. One of 
  the first ideas was about creating a smart CPI capable of proxying some requests
  to make use of physical hardware. This could be a different approach to have a CPI 
  able to deploy VMs and physical servers using the same BOSH Director. One could 
  have VMware/OpenStack Nova for VMs and Ironic for special jobs (like Cloud Foundry 
  runners). The CPI would delegate the calls on the other one for VM management. 
  Anyway, there are plans to support multi-CPI in BOSH, so I think this project will
  be focused only on Ironic.

* Make most of the [Ironic Standalone project](https://github.com/jriguera/ansible-ironic-standalone),
  in order to define a standard way to manage physical servers using Ironic as backend.
  Apart of having provisioning tools (Ansible, or other programs) using the Ironic 
  HTTP API to manage physical servers, this will bring the oportunity of managing
  the physical servers in a centralized way with Ironic. Ironic supports multiple
  Conductors (or even by using the concept of `chassis`) it is easy to use them
  as Availability Zones within BOSH.

* Be able to manage a pool of physical servers in a awesome way (also really
  slow way :-)


This project is made with Python ... I know most of the CPIs are written in
Ruby or Golang, so why Python? ... why not? It is a great language which does 
not need to be compiled, OpenStack is made with it and its libraries provide 
the functionality I needed (e.g. to create ConfigDrive(s)). Also, having a CPI 
in another language made with a different approach helps to define a way to 
document and understand the functionalities. The architecture of the source 
code `src/bosh_ironic_cpi` was created in a flexible way to be re-used, to 
write a new CPI, one only needs to create or change the `CPIAction` sub-classes 
defined in `src/bosh_ironic_cpi/ironic_cpi/actions/` folder, each one on each 
file. Each class will be registered automatically and the exceptions and/or 
returns will be transformed in JSON format and write via *STDOUT/STDERR*. 
This was a hacking project, made to understand the BOSH internal workflow, 
I have not got enough time to focus on writing the (needed) tests :-/



# General considerations

Before running this sofware, take into account:


* Servers must be predefined on Ironic (as *manageable* state) or defined
  using the **ironic_params** properties. When the CPI runs, depending on the
  configuration, it wil take one of the available servers which fits with the
  properties (searching by MAC or by hardware specs: memory, cpu, disk ...) or
  it will define the baremetal server in Ironic. When the CPI will delete
  the node, it will remember if the server was predefined to avoid removing
  it from Ironic.

* Baremetal servers need at least two disks. Because of how Bosh Agent works
  and how Ironic sets-up the ConfigDrive (as a small partition at the end of the
  first device */dev/sda*), Bosh Agent is not able to manage partitions in
  such way on the first device, as consecuence, a second device (*/dev/sdb*)
  is needed for ephemeral data. A 3rd device would be used for persistent data.

* The CPI can deploy normal OpenStack stemcells. They work on most of the
  hardware, but take into account there are some NICs or storage devices which
  would need aditional drivers. In that case, you will need to build your own
  stemcell including those drivers.

* A physical server usually has several NICs available, but maybe some of them
  are not connected or not needed. When BOSH Agent runs, it ensures all the
  interfaces defined on the server must have an IP, if an NIC has no IP address,
  Bosh Agent fails. To overcome this limitation I have decided to assign an IP
  of the loopback local range `127.0.0.100/24` to the non used interfaces.
  That is why all the MAC addresses must be defined (or discovered) in Ironic,
  to create such static network definitions.

* Bonding is needed! In the VM world it does not make sense, but in the
  physical worl, most of the times is desirable (unless there are a lot of
  servers and by taking aggregations one can assume losing some of them). In
  order to provide bonding, stemcells must be created with the proper settings
  and BOSH Agent functionality should be changed. A similar issue appears if
  one needs to define VLANs (besides the option of having OpenStack Neutron
  controlling the physical switch ports) for some NIC(s).

* Limited support for persistent disks. Persistent disks are local to each server.
  A persistent disk device (usually `/dev/sdc`) cannot be attached or moved to a
  different server than the one where it was originally created, because is
  physically attached to the server. If a job uses a persistent disk and a pool
  of  servers is defined, the CPI will select always the server where the disk
  lives: the MAC address of the server is encoded in the disk id, that is how
  to setup the nexus between persistent disk and server.

* LVM and/or RAID are not supported. LVM would be nice, but I think it will
  require a lot of changes in BOSH Agent which makes no sense to enable support
  in a ephemeral world. RAID setup could be managed by Ironic if the servers
  are predefined.



# Jobs defined in the release


This BOSH Release has two jobs. **ironic_cpi**, the important one, is the
implementation of the Ironic CPI. **webdav_metadata_registry** is an optional
job implementing the BOSH Registry API in Lua for Nginx. Making the most of the
WebDAV protocol (which is already needed to manage the Config-Drive Metatata
in Ironic Standalone) I have decided to create a simple implementation of the
Registry API to delegate in WebDAV as backend.

BOSH Registry stores a JSON *settings* needed by the Bosh Agent to carry on
with the configuration the VM. These JSON seetings are really simple, no
database is needed, it is possible to use WebDAB as storage already needed
for the stemcells. The Lua implementation just does internal redirections to 
WebDAV metadata location, doing some checks and creating the JSON file. 
There are two ideas behing this implementation:

  * To run this Lua program in a external NGINX server, the one which provides
  the ConfigDrive Metadata, and storage for the server images. Ironic 
  Config-Drive Metadata and Stemcell storage can live in the same server
  as the Registry API, centralizing all BOSH Agent specifications for every
  node in the same repository. The implementation is already included in 
  https://github.com/jriguera/ansible-ironic-standalone, just run the
  `setup-ironic-bosh-registry.yml` playbook after changing/defining the
  Registry credentials of the BOSH Director.
  
  * Run the WebDAV inside BOSH Director VM providing Stemcell and Config-Drive
  Metadata storage together with the Registry API. If you are running Ironic
  as part of a big OpenStack deployment, this is the way to use this CPI.
  For now, it only supports WebDAV storage repositories (no Glance) for 
  Stemcells and Ironic Config-Drive.


## Example set-up and configuration

Use BOSH Init as described in https://bosh.io/docs/init.html . Remember BOSH
Init will use two CPIs, one just to deploy the BOSH Director VM and the `ironic_cpi`
to be included on it. Follow the instructions for the platform you want to
run the BOSH Director VM and change the settings below.


First of all, you  have to add the `ironic_cpi` release to the releases section
like this:

```
releases:
- name: bosh
  url: https://bosh.io/d/github.com/cloudfoundry/bosh?v=257.9
  sha1: 3d6168823f5a8aa6b7427429bc727103e15e27af
- name: bosh-vsphere-cpi
  url: https://bosh.io/d/github.com/cloudfoundry-incubator/bosh-vsphere-cpi-release?v=27
  sha1: 7b9cd2b47138b49cdf9c7329ec6d85324d572743
- name: ironic_cpi
  url: http://10.0.0.0/images/ironic_cpi-0+dev.13.tgz
  sha1: 9b5a44903b75fcf31d12d735769dffdc40810248
```

Now, add the new jobs to the section `templates` from this release. Only 
one `*_cpi` job is needed in this section:

```
jobs:
- name: bosh
  instances: 1

  templates:
  - {name: nats, release: bosh}
  - {name: postgres, release: bosh}
  - {name: blobstore, release: bosh}
  - {name: director, release: bosh}
  - {name: health_monitor, release: bosh}
  - {name: ironic_cpi, release: ironic_cpi}
  - {name: webdav_metadata_registry, release: ironic_cpi}
```

Remember, the job *webdav_metadata_registry* is not needed if you are using 
[Ironic Standalone](https://github.com/jriguera/ansible-ironic-standalone) and
it was deployed with [setup-ironic-boshregistry.yml](https://github.com/jriguera/ansible-ironic-standalone/blob/master/setup-ironic-boshregistry.yml)
following [these instructions](https://github.com/jriguera/ansible-ironic-standalone#about-bosh),
otherwise just include it.


In the director section, make sure you have changed the `cpi_job` to point
to *ironic_cpi* job/template:

```
    director:
      address: 127.0.0.1
      name: ironic-bosh
      db: *db
      cpi_job: ironic_cpi
      user_management:
        provider: local
        local:
          users:
          - {name: admin, password: admin}
          - {name: hm, password: hm-password}
```


At the same indentation level, define the configuration properties:

```
    ironic_cpi:
      ironic_url: "http://IRONIC-API:6385/"
      ironic_auth_token: "fake"
      repository_stemcell_url: "http://IRONIC-API/images"
      repository_metadata_url: "http://IRONIC-API/metadata"
      metadata_publickeys:
      - "ssh-rsa AAAAB3NzaC1yc ... dsfasdfa"
      metadata_nameservers: ["8.8.8.8", "4.4.4.4"]
```

Change `IRONIC-API` with the IP address or dns name of Ironic API. If you are
not using Ironic Standalone (so also *webdav_metadata_registry* job), put here
the IP of the Registry specified in `registry.host` item.


Done!, now just deploy bosh: `bosh-init deploy <manifest.yaml>`, it will take
half an hour, so for a coffee! There are examples of manifests for different
platforms in the `checks` folder.


## Cloud-Config setup

Before starting using the new BOSH Director, you should load a cloud-config definition
to describe the infrastructure, example:

```
azs:
- name: dogo
  cloud_properties:
    availability_zone: dogo

vm_types:
- name: pe-prod-dogo-lab-01
  cloud_properties:
    macs: ['e4:1f:13:e6:33:3c']
    ironic_params:
      driver: "agent_ipmitool"
      driver_info:
        ipmi_address: "10.0.0.3"
        ipmi_username: "admin"
        ipmi_password: "pass"
        deploy_kernel: "file:///var/lib/ironic/http/deploy/coreos_production_pxe.vmlinuz"
        deploy_ramdisk: "file:///var/lib/ironic/http/deploy/coreos_production_pxe_image-oem.cpio.gz"
- name: pe-prod-dogo-lab-02
  cloud_properties:
    macs: [ 'e4:1f:13:e6:d6:d4', 'e4:1f:13:e6:d6:d6', '00:0a:cd:26:f1:79', '00:0a:cd:26:f1:7a', 'e6:1f:13:e8:c4:eb']
    ironic_params:
      driver: "agent_ipmitool"
      driver_info:
        ipmi_address: "10.0.0.4"
        ipmi_username: "admin"
        ipmi_password: "pass"
        deploy_kernel: "file:///var/lib/ironic/http/deploy/coreos_production_pxe.vmlinuz"
        deploy_ramdisk: "file:///var/lib/ironic/http/deploy/coreos_production_pxe_image-oem.cpio.gz"
- name: pe-prod-dogo-lab-03
  cloud_properties:
    macs: ['e4:1f:13:e6:3d:38', 'e4:1f:13:e6:3d:3a', '00:0a:cd:26:f2:1c', '00:0a:cd:26:f2:1b']
    ironic_params:
      driver: "agent_ipmitool"
      driver_info:
        ipmi_address: "10.0.0.5"
        ipmi_username: "admin"
        ipmi_password: "pass"
        deploy_kernel: "file:///var/lib/ironic/http/deploy/coreos_production_pxe.vmlinuz"
        deploy_ramdisk: "file:///var/lib/ironic/http/deploy/coreos_production_pxe_image-oem.cpio.gz"
- name: mac-03
  cloud_properties:
    macs: ['e4:1f:13:e6:3d:38']
- name: pool-01
  cloud_properties:
    ironic_properties:
      local_gb: 500

disk_types:
- name: default
  disk_size: 10000
  cloud_properties:
    device: /dev/sda

networks:
- name: default
  type: manual
  subnets:
  - range: 10.0.0.0/24
    az: dogo
    name: pxe
    gateway: 10.0.0.1
    reserved:
      - 10.0.0.1-10.0.0.100
      - 10.0.0.150-10.0.0.255
    dns: [8.8.8.8]
    cloud_properties:
      macs: ['e4:1f:13:e6:3d:38']
    static:
      - 10.0.0.248
      - 10.0.0.249
      - 10.0.0.250
      - 10.0.0.251

- name: compilation
  type: dynamic

compilation:
  workers: 1
  reuse_compilation_vms: true
  vm_type: pe-prod-dogo-lab-02
  network: compilation
```




### Defining manually a pool of servers for cloud-config settings

Normally this should be done using Ironic-Inspector ...

```
############################ lab1

NAME=lab1
MAC="e4:1f:13:e6:33:3c e4:1f:13:e6:33:3e"
IPMI=10.10.0.203
IPMI_USER=admin
IPMI_PASS=pass

# Define the node
ironic node-create -n "$NAME" \
    -d agent_ipmitool \
        -i ipmi_address=$IPMI \
        -i ipmi_username=$IPMI_USER \
        -i ipmi_terminal_port=20010 \
        -i ipmi_password=$IPMI_PASS \
    -i deploy_kernel="file:///var/lib/ironic/http/deploy/coreos_production_pxe.vmlinuz" \
    -i deploy_ramdisk="file:///var/lib/ironic/http/deploy/coreos_production_pxe_image-oem.cpio.gz"

# Get the UUID
UUID=$(ironic node-list | awk "/$NAME/ { print \$2 }")

# Add hardware propeties
ironic node-update "$UUID" add \
    properties/memory_mb="100000" \
    properties/cpus="16" \
    properties/local_gb="256"

# Add ports (macs)
for m in $MAC; do
    ironic port-create -n "$UUID" -a "$m"
done

# Set to manageable state in order to make it discoverable by the CPI
# States flow: http://docs.openstack.org/developer/ironic/_images/states.svg
ironic node-set-provision-state "$UUID" manage


############################ lab2

NAME=lab2
MAC="e4:1f:13:e6:d6:d4 e4:1f:13:e6:d6:d6 00:0a:cd:26:f1:79 00:0a:cd:26:f1:7a e6:1f:13:e8:c4:eb"
IPMI=10.10.0.204
IPMI_USER=admin
IPMI_PASS=pass

# Define the node
ironic node-create -n "$NAME" \
    -d agent_ipmitool \
        -i ipmi_address=$IPMI \
        -i ipmi_username=$IPMI_USER \
        -i ipmi_terminal_port=20011 \
        -i ipmi_password=$IPMI_PASS \
    -i deploy_kernel="file:///var/lib/ironic/http/deploy/coreos_production_pxe.vmlinuz" \
    -i deploy_ramdisk="file:///var/lib/ironic/http/deploy/coreos_production_pxe_image-oem.cpio.gz"

# Get the UUID
UUID=$(ironic node-list | awk "/$NAME/ { print \$2 }")

# Add hardware propeties
ironic node-update "$UUID" add \
    properties/memory_mb="200000" \
    properties/cpus="32" \
    properties/local_gb="512"

# Add ports (macs)
for m in $MAC; do
    ironic port-create -n "$UUID" -a "$m"
done

# Set to manageable state in order to make it discoverable by the CPI
# States flow: http://docs.openstack.org/developer/ironic/_images/states.svg
ironic node-set-provision-state "$UUID" manage


############################ List nodes

ironic node-list
# +--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+
# | UUID                                 | Name   | Instance UUID                        | Power State | Provisioning State | Maintenance |
# +--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+
# | 78eafda7-e89a-4eec-a65e-29fac864088c | lab1   | None                                 | power off   | manageable         | False       |
# | 5958d8a1-4df7-406e-ae06-30f4bd44f1cf | lab2   | None                                 | power off   | manageable         | False       |
# +--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+
```




# Local Dev environment

Run `bosh_prepare` to download the sources for the packages.


