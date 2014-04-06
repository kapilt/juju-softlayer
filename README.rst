Juju SoftLayer Provider
-----------------------

.. image:: doc/softlayer.png
   :target: here_


This package provides a cli plugin for juju that allows for automated
provisioning of machines on softlayer. I like to call it slayer :-)

Softlayer is premium hosting provider offering both bare metal and xen
based cloud instances with a myriad of configuration options across
multiple data center with monthly and hourly billing. Due to the length
of time it takes to provision bare metal machines (3-4 hrs) this plugin
only supports cloud instances.

Juju provides for workloads management and orchestration using a
collection of workloads definitions (charms) that can be assembled
lego fashion at runtime into complex application topologies.

You can find out more about juju at its home page. http://juju.ubuntu.com


Install
=======

**This plugin requires version of recent juju (>= 1.18)**

A suitable version is distributed for trusty (14.04) for older versions of ubuntu the latest stable release
are available from a ppa::

  $ sudo add-apt-repository ppa:juju/stable
  $ apt-get update && apt-get install juju
  $ juju version
  1.18.0-saucy-amd64

Plugin installation is done via pip/easy_install which is the python language
package managers, its available by default on ubuntu. Also recommended
is virtualenv to sandbox this install from your system packages::

  $ pip install -U juju-slayer

Fwiw, currently the transitive dependency tree is PyYAML, requests, softlayer.


Setup
=====

There are three steps for configuration and setup of this
provider. Configuring your softlayer api keys, adding an
environment to juju's config file, and setting up an ssh key for usage
on softlayer machines.

SoftLayer API Keys
++++++++++++++++++

A SoftLayer account is a pre-requisite, If you don't have a
Softlayer account you can sign up `here`_.

Credentials for the digital ocean api can be obtained from your account
dashboard at https://manage.softlayer.com/Administrative/apiKeychain

The credentials can be provided to the plugin via env variable or via the `sl`
cli's config

  - Environment variables SL_API_KEY and SL_USERNAME

This softlayer plugin uses the manual provisioning capabilities of
juju core. As a result its required to allocate machines in the
environment before deploying workloads. We'll explore that more in a
moment.

SSH Key
+++++++

An ssh key is required for use by this plugin and the public key
must be uploaded to the softlayer control panel, alternatively
you can upload it directly using the `sl` cli program (installed automatically 
as a pre-requisite of this plugin)::

   $ sl sshkey add $USER-key -f ~/.ssh/id_rsa.pub 

Keys can be verified with::

   $ sl sshkey list 

By default all keys in the softlayer account will be added to launched
nodes, so no explict user configuration is needed. A specific key to
utilize can be specified with the environment variable
SOFTLAYER_SSH_KEY="key_spec" where key_spec is either the id of the
key in the from the command line, or the name of the key as found in
softlayer control panel (https://manage.softlayer.com/Security/sshKeys)


Juju Config
+++++++++++

Next let's configure a juju environment for soft laayer, add an
a null provider environment to 'environments.yaml', for example::

 environments:
   softlayer:
      type: manual
      bootstrap-host: null
      bootstrap-user: root

Usage
=====

We need to tell juju which environment we want to use, there are
several ways to do this, either of the following will do the trick::

  $ juju switch softlayer
  $ export JUJU_ENV=softlayer

Now we can bootstrap our softlayer environment::

  $ juju sl bootstrap --constraints="mem=2g, region=sjc"

Which will create a machine with 2Gb of ram in the san jose data center.

All machines created by this plugin will have the juju environment
name as a prefix for their hostname if your looking at the softlayer
control panel and a suffix/domain of juju.ubuntu.

After our environment is bootstrapped we can add additional machines
to it via the the add-machine command, for example the following will
add 3 machines with 2Gb each::

  $ juju sl add-machine -n 2 --constraints="mem=2G, region=sjc"
  $ juju status

  environment: softlayer
  machines:
    "0":
      agent-state: started
      agent-version: 1.18.0.1
      dns-name: 162.243.115.78
      instance-id: 'manual:'
      series: precise
      hardware: arch=amd64 cpu-cores=1 mem=2002M
    "1":
      agent-state: started
      agent-version: 1.18.0.1
      dns-name: 162.243.86.238
      instance-id: manual:162.243.86.238
      series: precise
      hardware: arch=amd64 cpu-cores=1 mem=2002M
    "2":
      agent-state: started
      agent-version: 1.18.0.1
      dns-name: 107.170.39.10
      instance-id: manual:107.170.39.10
      series: precise
      hardware: arch=amd64 cpu-cores=1 mem=2002M
  services: {}

We can now use standard juju commands for deploying service workloads aka
charms::

  $ juju deploy wordpress

Without specifying the machine to place the workload on, the machine
will automatically go to an unused machine within the environment.

There are hundreds of available charms ready to be used, you can
find out more about what's out there from http://jujucharms.com
Or alternatively the 'plain' html version at
http://manage.jujucharms.com/charms/precise

We can use manual placement to deploy target particular machines::

  $ juju deploy mysql --to=2

And of course the real magic of juju comes in its ability to assemble
these workloads together via relations like lego blocks::

  $ juju add-relation wordpress mysql

We can terminate allocated machines by their machine id. By default with the
softlayer plugin, machines are forcibly terminated which will also terminate any
service units on those machines::

  $ juju sl terminate-machine 1 2

And we can destroy the entire environment via::

  $ juju sl destroy-environment

All commands have builtin help facilities and accept a -v option which will
print verbose output while running.

You can find out more about using from http://juju.ubuntu.com/docs

Constraints
===========

Constraints are selection criteria used to determine what type of
machine to allocate for an environment. Those criteria can be related
to size of the machine, its location, or other provider specific
criteria.

This plugin accepts the standard `juju constraints`_

  - cpu-cores
  - memory
  - root-disk

Additionally it supports the following provider specific constraints.

  - 'region' to denote one softlayer's data center to utilize. All softlayer
    data centers are supported and various short hand aliases are defined. ie. valid
    values include ams01, dal01, dal05, dal06, sea01, sng01, sjc01, wdc01. The 
    plugin defaults to leaving it empty which auto selects first available.


.. _here: https://www.softlayer.com/virtual-server
.. _juju constraints: https://juju.ubuntu.com/docs/reference-constraints.html
