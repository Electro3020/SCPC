# ------------ #
# EXPERIMENTAL #
# ------------ #

import kdl
import SCPC.util.data_types as dt

class Config:
    # TODO: find better way to do this
    # List of tuples (ID, class)
    id_map = []
    id_dict = {}
    VERSION_MAJOR = 0
    VERSION_MINOR = 0

cfg = Config()

class Packet:
    """The base class which will be populated on load"""
    id=0
    flags=[]
    idempotency=0
    fields={}
    type_name=""
    def __init__(self, **kwargs):
        for fname, ftype in self.fields.items():
            setattr(self, fname, getattr(dt, ftype).NATIVE_TYPE())

        for key, value in kwargs.items():
            setattr(self, key, value)

    def encode(self):
        """Encode a Packet"""
        # First, we need to construct the packet fields, then put together the header
        pkt_fields = bytes()
        for key, value in self.fields.items():
            pkt_fields += getattr(dt, value).encode(getattr(self, key)) # Encode the field into bytes and add to the end of pkt_fields
            # getattr(dt, i) is essentially the same as dt.i where i is the name of the field type
            # and getattr(packet, i) is packet.i where i is the field name

        encoded_pkt: bytes = dt.uint16.encode(cfg.VERSION_MAJOR) + dt.uint16.encode(cfg.VERSION_MINOR) + dt.uint16.encode(self.id)
        if 'i' in self.flags:
            encoded_pkt += dt.uint32.encode(self.idempotency)

        # Finally, construct the packet
        encoded_pkt += pkt_fields

        # Insert the final packet size
        size = dt.uint32.encode(len(encoded_pkt) + 4)
        return size + encoded_pkt

"""The classes which contains all packet types"""
class serverbound: pass
class clientbound: pass
class twoway: pass

class PacketReadError(Exception): pass

def init(config_file: str):
    # Load config file
    with open(config_file, 'rt') as _infile:
        pkt_cfg = kdl.parse(_infile.read())

    for i in pkt_cfg.nodes:
        if i.name == "version":
            cfg.VERSION_MAJOR = int(i.args[0])
            cfg.VERSION_MINOR = int(i.args[1])
            continue

        for n in i.nodes:
            # Create a dictionary of attributes for our new class
            attr_dict = {"id": int(n.args[0]), "fields": n.props, "type_name": n.name}

            if len(n.args) > 1: # has 'flags' argument
                attr_dict["flags"] = list(n.args[1])

            # Create a new class for the configured packet
            new_packet = type(n.name, (Packet, ), attr_dict)

            # new_packet is now a class with the name of what was given in packets.kdl and contains:
            # id: the ID as an int
            # flags: a list of single characters indicating the packet flags
            # fields: a dictionary of attribute names and the name of their types as defined in data_types.py

            # Assign the new packet class as an attribute
            if i.name == "serverbound":
                setattr(serverbound, n.name, new_packet)
                cfg.id_map.append((n.args[0], getattr(serverbound, n.name)))

            elif i.name == "clientbound":
                setattr(clientbound, n.name, new_packet)
                cfg.id_map.append((n.args[0], getattr(clientbound, n.name)))

            elif i.name == "twoway":
                setattr(twoway, n.name, new_packet)
                cfg.id_map.append((n.args[0], getattr(twoway, n.name)))

            # From another script, we can access e.g. packets.serverbound.connect.id and get 0x4002

    cfg.id_dict = dict(cfg.id_map)

def decode(packet: bytes):
    """Decode packet"""
    # Start by getting the header values and verifying them
    length = int.from_bytes(packet[0:4])
    if length != len(packet):
        raise PacketReadError(f"Mismatched packet length (expected {length}, got {len(packet)})")

    mv = int.from_bytes(packet[4:6])
    if mv != cfg.VERSION_MAJOR:
        raise PacketReadError(f"Mismatched packet major version (we're on v{cfg.VERSION_MAJOR}.{cfg.VERSION_MINOR}, packet's on v{mv})")

    packet_id = int.from_bytes(packet[8:10])

    packet_cls = cfg.id_dict[packet_id]() # Create a new Packet class instance

    i = 10
    if 'i' in packet_cls.flags:
        packet_cls.idempotency = packet[10:14]
        i += 4

    # Populate the packet class
    for fname, ftype in packet_cls.fields.items(): # fname = name of the packet field, ftype = data type of the field as defined in data_types.py
        fcls, inc = getattr(dt, ftype).decode(packet[i:]) # returns a tuple (data type value, number of bytes read from input)
        setattr(packet_cls, fname, fcls)

        i += inc

    return packet_cls

if __name__ == "__main__":
    # TODO: add tests
