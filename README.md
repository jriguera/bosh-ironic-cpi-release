# bosh-ironic-cpi

A Bosh CPI (Cloud Provider Interface) to manage baremetal servers via Ironic
(Standalone mode, without the rest of OpenStack components). The idea is make
the most of OpenStack Ironic to provide an alternative way to deploy physical
servers with Bosh. If you do not know about how amazing is Bosh, have a look
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
  URL        https://10.0.0.10:25555
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

Bosh perspective:

```
$ bosh instances
https://10.0.0.10:25555
Acting as user 'admin' on deployment 'carbon-c-relay' on 'ironic-bosh'

Director task 25720

Task 25720 done

+------------------------------------------------+---------+------+---------+---------------+
| Instance                                       | State   | AZ   | VM Type | IPs           |
+------------------------------------------------+---------+------+---------+---------------+
| test/0 (e633088f-11a9-4ee6-b26f-2388f29d2d1d)* | running | dogo | pool    | 10.0.0.250    |
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

* Hack "Day" (actually months) project to learn about Bosh internals. One of
  the first ideas was about creating a smart CPI capable of proxying some requests
  to make use of physical hardware. This could be a different approach to have a CPI
  able to deploy VMs and physical servers using the same Bosh Director. One could
  have VMware/OpenStack Nova for VMs and Ironic for special jobs (like Cloud Foundry
  runners). The CPI would delegate the calls on the other one for VM management.
  Anyway, there are plans to support multi-CPI in Bosh, so I think this project will
  be focused only on Ironic.

* Make most of the [Ironic Standalone project](https://github.com/jriguera/ansible-ironic-standalone),
  in order to define a standard way to manage physical servers using Ironic as backend.
  Apart of having provisioning tools (Ansible, or other programs) using the Ironic
  HTTP API to manage physical servers, this will bring the oportunity of managing
  the physical servers in a centralized way with Ironic. Ironic supports multiple
  Conductors (or even by using the concept of `chassis`) it is easy to use them
  as Availability Zones within Bosh.


This project is made with Python ... I know most of the CPIs are written in
Ruby or Golang, so why Python? ... why not? It is a great language which does
not need to be compiled, OpenStack is made with it and its libraries provide
the functionality I needed (e.g. to create ConfigDrive(s)). Also, having a CPI
in another language made with a different approach helps to define a way to
document and understand the functionalities. The architecture of the source
code `src/bosh_ironic_cpi` was created in a flexible way to be re-used, to
write a new CPI, one only needs to create or change the `CPIAction` sub-classes
defined in `src/bosh_ironic_cpi/ironic_cpi/actions/` folder, each one on each
file. Each class will be registered automatically and exceptions or returns will
be transformed in JSON format and write via **stdout** and **stderr**.
This was a hacking project, made to understand the Bosh internal workflow,
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
  are not connected or not needed. When Bosh Agent runs, it ensures all the
  interfaces defined on the server must have an IP, if an NIC has no IP address,
  Bosh Agent fails. To overcome this limitation I have decided to assign an IP
  of the loopback local range `127.0.0.100/24` to the non used interfaces.
  That is why all the MAC addresses must be defined (or discovered) in Ironic,
  to create such static network definitions.

* Bonding is needed! In the VM world it does not make sense, but in the
  physical worl, most of the times is desirable (unless there are a lot of
  servers and by taking aggregations one can assume losing some of them). In
  order to provide bonding, stemcells must be created with the proper settings
  and Bosh Agent functionality should be changed. A similar issue appears if
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
  require a lot of changes in Bosh Agent which makes no sense to enable support
  in a ephemeral world. RAID setup could be managed by Ironic if the servers
  are predefined.



# Jobs defined in the release

The Bosh Release consist of two jobs. The core, called **ironic_cpi**, is the
implementation of the Ironic CPI and **webdav_metadata_registry** is an optional
job implementing the Bosh Registry API in Lua for Nginx. Making the most of the
WebDAV protocol (which is already needed to manage the Config-Drive Metatata
in Ironic Standalone) I have decided to create a simple implementation of the
Registry API to delegate in WebDAV as backend.

Bosh Registry stores the *settings* needed by the Bosh Agent to carry on
with the configuration the VM. These settings are a simple JSON file, no
database is needed, it is possible to use WebDAB as storage already needed
for the stemcells. The Lua implementation parses each request and does internal
redirections to WebDAV metadata location, doing some checks and creating the
JSON file. There are two ideas behing this implementation:

  * The Registry API server can live in the same WebDAV service as Ironic
  Config-Drive **Metadata** and Stemcell **Images** storage, centralizing all
  Bosh Agent specifications for every node in the same repository. The
  implementation is already included in https://github.com/jriguera/ansible-ironic-standalone, just run the
  `setup-ironic-bosh-registry.yml` playbook after changing/defining the
  Registry credentials of the Bosh Director.
  [Instructions](https://github.com/jriguera/ansible-ironic-standalone#about-bosh).

  * Run the WebDAV inside Bosh Director VM providing Stemcell/Image and Config-Drive
  Metadata storage together with the Registry API. If you are running Ironic
  as part of a big OpenStack deployment, this is the way to use this CPI for now,
  because it only supports WebDAV storage repositories for Stemcells/Images and
  Ironic Config-Drive data (sorry no Glance, Swift  or S3).



## Example Bosh-Init set-up and configuration

Use Bosh Init as described in https://bosh.io/docs/init.html . Take into account,
Bosh-Init will use two CPIs, one just to deploy the Bosh Director VM and the
`ironic_cpi` to be included on it. Follow the instructions for the platform you
want to run the Bosh Director VM and change the settings below.


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
- name: bosh-ironic-cpi
  url: https://github.com/jriguera/bosh-ironic-cpi-release/releases/download/v1/bosh-ironic-cpi-1.tgz
  sha1: 5c361af42a2afcc9cdb9ef1d8a8420eabe7917c1
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
  - {name: ironic_cpi, release: bosh-ironic-cpi}
  - {name: webdav_metadata_registry, release: bosh-ironic-cpi}
```

Remember, job *webdav_metadata_registry* is not needed if you are using
[Ironic Standalone](https://github.com/jriguera/ansible-ironic-standalone) and
it was deployed with [setup-ironic-boshregistry.yml](https://github.com/jriguera/ansible-ironic-standalone/blob/master/setup-ironic-boshregistry.yml)
following [the instructions](https://github.com/jriguera/ansible-ironic-standalone#about-bosh),
otherwise just include both jobs.


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

At the same indentation level, define the main CPI configuration properties:

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
the IP of the Registry specified in `registry.host` item. `metadata_publickeys`
is a list of SSH public keys which will be incorporated to vcap user in the
servers deployed.

Done!, now just run Bosh-Init: `bosh-init deploy <manifest.yaml>`, it will take
half an hour, so for a coffee! There are examples of manifests for different
platforms in the `checks` folder.



## Stemcells

The CPI can operate with the OpenStack images, created with those parameters:

* Disk format: **qcow2**
* container Format: **bare**

```
bosh upload stemcell https://bosh.io/d/stemcells/bosh-openstack-kvm-ubuntu-trusty-go_agent
```

Those stemcells are optimized to run in KVM hypervisors, but because the Linux kernel
includes a lot of device drivers, they should run on most of the common hardware.
Take into account there is hardware which requires additional drivers or 
firmware to get it working, in such, case you will have to build your own stemcells.



## Cloud-Config setup

Focusing in Bosh v2 style manifests, before starting using the new Bosh Director,
you have to upload a cloud-config definition to describe and use the
infrastructure. Given the following example:

```
azs:
- name: dogo
  cloud_properties:
    availability_zone: dogo

vm_types:

# Define and use these servers in Ironic
- name: pe-prod-dogo-lab-01
  cloud_properties:
    macs: ['e4:1f:13:e6:33:3c']
    ironic_params:
      driver: "agent_ipmitool"
      driver_info:
        ipmi_address: "10.100.0.3"
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
        ipmi_address: "10.100.0.4"
        ipmi_username: "admin"
        ipmi_password: "pass"
        deploy_kernel: "file:///var/lib/ironic/http/deploy/ctinyipa-master.vmlinuz"
        deploy_ramdisk: "file:///var/lib/ironic/http/deploy/tinyipa-master.gz"
- name: pe-prod-dogo-lab-03
  cloud_properties:
    macs: ['e4:1f:13:e6:3d:38', 'e4:1f:13:e6:3d:3a', '00:0a:cd:26:f2:1c', '00:0a:cd:26:f2:1b']
    ironic_params:
      driver: "agent_ipmitool"
      driver_info:
        ipmi_address: "10.100.0.5"
        ipmi_username: "admin"
        ipmi_password: "pass"
        deploy_kernel: "file:///var/lib/ironic/http/deploy/ctinyipa-master.vmlinuz"
        deploy_ramdisk: "file:///var/lib/ironic/http/deploy/tinyipa-master.gz"

# Specific predefined server in Ironic
- name: e4-1f-13-e6-3f-42
  cloud_properties:
    macs: ['e4:1f:13:e6:3f:42']

# Pool definition
- name: pool
  cloud_properties:
    ironic_properties:
      local_gb: 500
      cpus: 16

# Persistent disk /dev/sdc (on each server)
disk_types:
- name: default
  disk_size: 1
  cloud_properties:
    device: /dev/sdc

# Two networks, Ironic DHCP pool to deploy and compile packages
# and static IPs for the jobs
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
      - 10.0.0.250
      - 10.0.0.251
- name: compilation
  type: dynamic

# The second server is reserved for compilation purposes, because it boots
# faster than the others ...
compilation:
  workers: 1
  reuse_compilation_vms: true
  vm_type: pe-prod-dogo-lab-02
  network: compilation
```

The sections are documented in https://bosh.io/docs/cloud-config.html , but
there are `cloud_properties` parameters for some of them which have to be
explained to understand the Bosh Ironic CPI functionalities.

Take into account that some properties depend on your hardware and Ironic
settings. Check the Ironic documentation to know more.


### *vm_types* section can be used in 3 different ways

* **To specifically define a server in Ironic**, such server can be referenced
  in the deployment manifest. You can define as many servers as you need, and,
  in the same way Bosh CPI defines each server, it will be deleted from Ironic
  when it will be no longer needed in the deployment manifest. All the
  configuration remains in Bosh Cloud-Config.
  ```
  - name: pe-prod-dogo-lab-03
    cloud_properties:
      macs: ['e4:1f:13:e6:3d:38', 'e4:1f:13:e6:3d:3a', '00:0a:cd:26:f2:1c', '00:0a:cd:26:f2:1b']
      ironic_params:
        driver: "agent_ipmitool"
        driver_info:
          ipmi_address: "10.100.0.5"
          ipmi_username: "admin"
          ipmi_password: "pass"
          deploy_kernel: "file:///var/lib/ironic/http/deploy/ctinyipa-master.vmlinuz"
          deploy_ramdisk: "file:///var/lib/ironic/http/deploy/tinyipa-master.gz"
  ```
  Two parameters must be defined in cloud properties: **macs** a list of all
  the MAC addresses of the physical server (even if they will not be used,
  in such case, an IP of the local loopback range will be assigned, see
  *General  considerations* section above) and **ironic_params** is a dictionary
  of parameters for Ironic, basically the IPMI settings of the physical server
  and the image used to deploy the stemcell. `ironic_params` values depends on
  the physical server and Ironic configuration, it can include all the
  parameters supported by the [ironic.node.create](http://docs.openstack.org/developer/python-ironicclient/api/ironicclient.v1.node.html) API method such as: `chassis_uuid`, `driver`, `driver_info`,
  `extra`, `uuid`, `properties`, `name`, `network_interface`, `resource_class`.
  The example configuration here should be enough for most of the cases, just
  change the MACs and the IPMI parameters acording to your server, for more
  information, check https://github.com/openstack/python-ironicclient/blob/master/ironicclient/v1/node.py
  and https://github.com/jriguera/ansible-ironic-standalone

* **To reference a predefined server by MAC**. In this case, Bosh CPI will perform
  a search over all physical servers defined in Ironic which are in state *available*
  (not in use). Specific parameters of the selected server are already defined in
  Ironic (IPMI and driver_info settings) and Bosh CPI does not touch and know
  them. When the server is not longer needed by Bosh, it will be put in *available*
  state again, ready to be used. This mode is useful to target a specific server
  for a deployment.
  ```
  - name: e4-1f-13-e6-3f-42
    cloud_properties:
      macs: ['e4:1f:13:e6:3f:42']
  ```
  Only one parameter is needed: **macs**, a list of macs to search the server
  (or servers) pre-defined in Ironic. The first *available* server which
  has one of the MACs will be used.

* **To define a pool of pre-defined servers by hardware properties**. Similar to
  the previous use case, but instead of searching by MAC, Bosh CPI will search
  for a server which fits on the hardware properties required. The server has
  to be in *manageable* state to be selected. By using [Ironic-Inspector](http://docs.openstack.org/developer/ironic-inspector/)
  to automatically discover and define the new servers in Ironic, without human
  intervention, they will become ready to use by Bosh CPI. Example:
  ```
  - name: pool
    cloud_properties:
      ironic_properties:
        local_gb: 500
        cpus: 16
  ```
  This will define a selection pool with two filters: `local_gb` wich will filter
  servers with at least 500 GB of disk storage and `cpus` which will select
  those ones with at least 16 cpus. The **ironic_properties** available are:
  `memory_mb`, `cpu_arch`, `local_gb`, `cpus` which are the same properties
  used by OpenStack Nova Scheduler as well the ones automatically defined
  by Ironic Inspector. When server is no longer needed, Bosh CPI will move it
  back to the pool.


### *disk_types* section

Persistent disks are local to the server where it was originally created. There
is no way to attach a physical disk to a different server (without using
network tecnologies). If a job uses a persistent disk and a pool of  servers
is defined, the CPI will select always the server where the disk lives:
the MAC address of the server is encoded in the disk id, that is how to setup
the nexus between persistent disk and server.

Because of the combination of how Bosh Agent works and the Config-Drive
partition created by Ironic driver at the end of the device where the stemcell
is deployed, Bosh Agent cannot handle ephemeral partitions on the same disk,
causing that a server needs at least 2 disks: `/dev/sda` for the operating
system, `/dev/sdb` for ephemeral data like swap and logs. With this mapping,
the next available disk is `/dev/sdc` (for persistent data):

```
- name: default
  disk_size: 1
  cloud_properties:
    device: /dev/sdc
```

The parameter `disk_size` does not make sense here, but it is required. The
device is already physically attached to the server, and the size is determined
by its capabilities. The parameter `device` is not required, if it is not
present, the default value is `/dev/sdc`.

Also, there is a limitation naming the devices. Bosh Agent assumes always
devices like 'sdX', and when it creates the partitions on the disk, it assumes
the partitions will be named as `sdX1`, `sdX2` ... if you specify a device like
`/dev/disk/by-id/scsi....` it will not fit with the partition schema and bosh
Agent will fail. You have to specify devices with format '/dev/sdX' here. Moreover,
be aware those devices can point to a different physical devices when the stemcell
is being deployed vs when the stemcell runs. The kernel used to deploy the
stemcells can discover the devices in a different order than the kernel of
the stemcell, so it could happen that the ephemeral device would be `/dev/sda`,
check the BIOS settings to change the order.


### *networks* section

Different networks definition are supported, it is only limited by the
configuration of network devices (switches, routers, ...) connected to the NICs.
Usually networks used for compilacion can be `dynamic`, which means the IPs
will be assigned from the DHCP pool of Ironic (check its configuration).

Example:
```
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
      - 10.0.0.250
      - 10.0.0.251
- name: compilation
  type: dynamic
```

There is only one parameter available for *cloud properties* here: `macs`, a
list of MACs addresses from different servers which should be used in the present
network. The list allows to determine which NICs (from the servers) must be
assigned to each network, in case of a server with multiple NICs and connected
to multiple networks.

A simple solution to avoid this weird setting could be allow an extra
parameter in the [*networks* block of the manifest](https://bosh.io/docs/manifest-v2.html#instance-groups)
to specify the MAC address, or allow the MAC address as a parameter in the
`networks.default` array (apart of `dns` and `gateway`).


### Defining manually a pool of physical servers

Normally this task should be done automatically by Ironic-Inspector, but those
are the Ironic commands to do it manually. Change the variables and properties
according to each one:

```
### lab1

NAME=lab1
MAC="e4:1f:13:e6:44:6a e4:1f:13:e6:44:6b"
IPMI=10.100.0.203
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


### lab2

NAME=lab2
MAC="e4:1f:13:e6:44:d4 e4:1f:13:e6:44:d6 00:0a:cd:26:44:79 00:0a:cd:26:44:7a e6:1f:13:e8:44:eb"
IPMI=10.100.0.204
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


### List nodes

ironic node-list
# +--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+
# | UUID                                 | Name   | Instance UUID                        | Power State | Provisioning State | Maintenance |
# +--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+
# | 78eafda7-e89a-4eec-a65e-29fac864088c | lab1   | None                                 | power off   | manageable         | False       |
# | 5958d8a1-4df7-406e-ae06-30f4bd44f1cf | lab2   | None                                 | power off   | manageable         | False       |
# +--------------------------------------+--------+--------------------------------------+-------------+--------------------+-------------+
```



# Dev environment

Run `./bosh_prepare download` to download the sources of the packages.
In the `examples` folder there are example manifests to check the jobs with Bosh Lite.



## Known issues

Since Bosh Agent assumes that new disks are always empty and clean (specially the
ephemeral one), some old versions will fail to deploy because they try to
create some folders which are there. There are two workarounds for this issue:

* Delete (or overwrite with `dd`) the ephemeral disk manually.
* Setup Ironic clean steps to automatically delete disks when the node is deleted. This
is the implemented solution. The clean steps incorporated in the current stable Ironic
only supports wiping disks and this operation takes a lot of time!. The new version
adds an additional clean step which only destroys the partitions tables, which is
faster than wiping the disk (and enough for this purpose). The clean steps can be
defined in Ironic or in the CPI via configuration parameters. More info:
http://docs.openstack.org/developer/ironic/deploy/cleaning.html



## TODO

* Write code tests
* Find out how to support bonding on the Stemcells
* Create specific stemcells for Ironic
* Support for non defined NICs*
* Create a specific stemcell for Ironic
* VLANs support?*
* Include RAID setup in predefined servers

\* Changes in the Bosh Agent are required



# Author & License

José Riguera López

Apache 2.0
