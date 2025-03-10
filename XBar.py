from MemObject import MemObject
from System import System
from m5.params import *
from m5.proxy import *
from m5.SimObject import SimObject

class BaseXBar(MemObject):
    type = 'BaseXBar'
    abstract = True
    cxx_header = "mem/xbar.hh"

    slave = VectorSlavePort("Vector port for connecting masters")
    master = VectorMasterPort("Vector port for connecting slaves")

    # Latencies governing the time taken for the variuos paths a
    # packet has through the crossbar. Note that the crossbar itself
    # does not add the latency due to assumptions in the coherency
    # mechanism. Instead the latency is annotated on the packet and
    # left to the neighbouring modules.
    #
    # A request incurs the frontend latency, possibly snoop filter
    # lookup latency, and forward latency. A response incurs the
    # response latency. Frontend latency encompasses arbitration and
    # deciding what to do when a request arrives. the forward latency
    # is the latency involved once a decision is made to forward the
    # request. The response latency, is similar to the forward
    # latency, but for responses rather than requests.
    frontend_latency = Param.Cycles("Frontend latency")
    forward_latency = Param.Cycles("Forward latency")
    response_latency = Param.Cycles("Response latency")

    # Width governing the throughput of the crossbar
    width = Param.Unsigned("Datapath width per port (bytes)")

    # The default port can be left unconnected, or be used to connect
    # a default slave port
    default = MasterPort("Port for connecting an optional default slave")

    # The default port can be used unconditionally, or based on
    # address range, in which case it may overlap with other
    # ports. The default range is always checked first, thus creating
    # a two-level hierarchical lookup. This is useful e.g. for the PCI
    # xbar configuration.
    use_default_range = Param.Bool(False, "Perform address mapping for " \
                                       "the default port")

class NoncoherentXBar(BaseXBar):
    type = 'NoncoherentXBar'
    cxx_header = "mem/noncoherent_xbar.hh"

class CoherentXBar(BaseXBar):
    type = 'CoherentXBar'
    cxx_header = "mem/coherent_xbar.hh"

    # The coherent crossbar additionally has snoop responses that are
    # forwarded after a specific latency.
    snoop_response_latency = Param.Cycles("Snoop response latency")

    # An optional snoop filter
    snoop_filter = Param.SnoopFilter(NULL, "Selected snoop filter")

    # Determine how this crossbar handles packets where caches have
    # already committed to responding, by establishing if the crossbar
    # is the point of coherency or not.
    point_of_coherency = Param.Bool(False, "Consider this crossbar the " \
                                    "point of coherency")

    # Specify whether this crossbar is the point of unification.
    point_of_unification = Param.Bool(False, "Consider this crossbar the " \
                                      "point of unification")

    system = Param.System(Parent.any, "System that the crossbar belongs to.")

class SnoopFilter(SimObject):
    type = 'SnoopFilter'
    cxx_header = "mem/snoop_filter.hh"

    # Lookup latency of the snoop filter, added to requests that pass
    # through a coherent crossbar.
    lookup_latency = Param.Cycles(1, "Lookup latency")

    system = Param.System(Parent.any, "System that the crossbar belongs to.")

    # Sanity check on max capacity to track, adjust if needed.
    max_capacity = Param.MemorySize('8MB', "Maximum capacity of snoop filter")

# We use a coherent crossbar to connect multiple masters to the L2
# caches. Normally this crossbar would be part of the cache itself.
class L2XBar(CoherentXBar):
    # 256-bit crossbar by default
    width = 32

    # Assume that most of this is covered by the cache latencies, with
    # no more than a single pipeline stage for any packet.
    frontend_latency = 1
    forward_latency = 0
    response_latency = 1
    snoop_response_latency = 1

    # Use a snoop-filter by default, and set the latency to zero as
    # the lookup is assumed to overlap with the frontend latency of
    # the crossbar
    snoop_filter = SnoopFilter(lookup_latency = 0)

    # This specialisation of the coherent crossbar is to be considered
    # the point of unification, it connects the dcache and the icache
    # to the first level of unified cache.
    point_of_unification = True
class L3XBar(CoherentXBar):
    # 256-bit crossbar by default
    width = 32
 
    # Assume that most of this is covered by the cache latencies, with
    # no more than a single pipeline stage for any packet.
    frontend_latency = 1
    forward_latency = 0
    response_latency = 1
    snoop_response_latency = 1

# One of the key coherent crossbar instances is the system
# interconnect, tying together the CPU clusters, GPUs, and any I/O
# coherent masters, and DRAM controllers.
class SystemXBar(CoherentXBar):
    # 128-bit crossbar by default
    width = 16

    # A handful pipeline stages for each portion of the latency
    # contributions.
    frontend_latency = 3
    forward_latency = 4
    response_latency = 2
    snoop_response_latency = 4

    # Use a snoop-filter by default
    snoop_filter = SnoopFilter(lookup_latency = 1)

    # This specialisation of the coherent crossbar is to be considered
    # the point of coherency, as there are no (coherent) downstream
    # caches.
    point_of_coherency = True

    # This specialisation of the coherent crossbar is to be considered
    # the point of unification, it connects the dcache and the icache
    # to the first level of unified cache. This is needed for systems
    # without caches where the SystemXBar is also the point of
    # unification.
    point_of_unification = True

# In addition to the system interconnect, we typically also have one
# or more on-chip I/O crossbars. Note that at some point we might want
# to also define an off-chip I/O crossbar such as PCIe.
class IOXBar(NoncoherentXBar):
    # 128-bit crossbar by default
    width = 16

    # Assume a simpler datapath than a coherent crossbar, incuring
    # less pipeline stages for decision making and forwarding of
    # requests.
    frontend_latency = 2
    forward_latency = 1
    response_latency = 2
