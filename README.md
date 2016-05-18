# bosh-ironic-cpi

A Bosh CPI to manage baremetal servers using Ironic (Standalone).

Tested using https://github.com/jriguera/ansible-ironic-standalone


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

WORK IN PROGRESS.

TODO: Registry integration


# bosh-init example on VMware

``` 
---
name: bosh

releases:
- name: bosh
  url: https://bosh.io/d/github.com/cloudfoundry/bosh?v=256.2
  sha1: ff2f4e16e02f66b31c595196052a809100cfd5a8
- name: bosh-vsphere-cpi
  url: https://bosh.io/d/github.com/cloudfoundry-incubator/bosh-vsphere-cpi-release?v=22
  sha1: dd1827e5f4dfc37656017c9f6e48441f51a7ab73
- name: ironic_cpi
  url: http://10.230.44.252/images/ironic_cpi-0+dev.14.tgz
  sha1: c1058ce4b783dd5f04c396a6852733f4b40e875b


vcenter: &vcenter
  address: 10.3.3.79
  user: sa_bosh
  password: springer01
  datacenters:
  - name: Timecops
    vm_folder: vms
    template_folder: templates
    datastore_pattern: timecops
    persistent_datastore_pattern: timecops
    disk_path: disks
    clusters: [Timecops]

resource_pools:
- name: vms
  network: private
  stemcell:
    url: https://bosh.io/d/stemcells/bosh-vsphere-esxi-ubuntu-trusty-go_agent?v=3232.4
    sha1: 27ec32ddbdea13e3025700206388ae5882a23c67
  cloud_properties:
    cpu: 2
    ram: 4_096
    disk: 20_000
  env:
    bosh:
      # c1oudc0w is a default password for vcap user
      password: "$6$4gDD3aV0rdqlrKC$2axHCxGKIObs6tAmMTqYCspcdvQXh3JJcvWOY2WGb4SrdXtnCyNaWlrf3WEqvYR2MYizEGp3kMmbpwBC6jsHt0"

disk_pools:
- name: disks
  disk_size: 20_000

networks:
- name: private
  type: manual
  subnets:
  - range: 10.230.0.0/24
    gateway: 10.230.0.1
    dns: [8.8.8.8]
    reserved: [10.230.0.1-10.230.0.200, 10.230.0.210-10.230.0.255]
    cloud_properties:
      name: Timecops-Admin-500

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

  resource_pool: vms
  persistent_disk_pool: disks

  networks:
  - name: private
    static_ips: [10.230.0.31]

  properties:
    nats:
      address: 127.0.0.1
      user: nats
      password: nats-password

    postgres: &db
      listen_address: 127.0.0.1
      host: 127.0.0.1
      user: postgres
      password: postgres-password
      database: bosh
      adapter: postgres

    blobstore:
      address: 10.230.0.31
      port: 25250
      provider: dav
      director: {user: director, password: director-password}
      agent: {user: agent, password: agent-password}

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

    hm:
      director_account: {user: hm, password: hm-password}
      resurrector_enabled: true

    ironic_cpi:
      ironic_url: "http://10.230.44.252:6385/"
      ironic_auth_token: " "
      repository_stemcell_url: "http://10.230.44.252/images"
      repository_metadata_url: "http://10.230.44.252/metadata"
      registry_url: "http://10.230.44.252/registry"
      registry_endpoint: "http://10.230.44.252/registry"

    agent:
      mbus: "nats://nats:nats-password@10.230.0.31:4222"

    ntp: &ntp [0.pool.ntp.org, 1.pool.ntp.org]

cloud_provider:
  template:
    name: vsphere_cpi
    release: bosh-vsphere-cpi
  mbus: "https://mbus:mbus-password@10.230.0.31:6868"
  properties:
    vcenter: *vcenter
    agent:
      mbus: "https://mbus:mbus-password@0.0.0.0:6868"
    blobstore:
      provider: local
      path: /var/vcap/micro_bosh/data/cache
    ntp: *ntp
```
