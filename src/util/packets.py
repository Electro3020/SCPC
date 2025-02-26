# ------------ #
# EXPERIMENTAL #
# ------------ #

import kdl
import data_types as dt

class Packet:
    """The base class which will be populated on load"""
    id=0
    flags=[]
    idempotency=0
    fields={}

VERSION_MAJOR = 0
VERSION_MINOR = 0

"""The classes which contains all packet types"""
class serverbound: pass
class clientbound: pass
class twoway: pass

class PacketReadError(Exception): pass

# Load config file
with open("res/util/packets.kdl", 'r') as _infile:
    pkt_cfg = kdl.parse(_infile.read())

# List of tuples (ID, class)
id_map = []

for i in pkt_cfg.nodes:
    if i.name == "version":
        VERSION_MAJOR = int(i.args[0])
        VERSION_MINOR = int(i.args[1])
        continue

    for n in i.nodes:
        # Create a dictionary of attributes for our new class
        attr_dict = {"id": int(n.args[0]), "fields": n.props}

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
            id_map.append((n.args[0], getattr(serverbound, n.name)))

        elif i.name == "clientbound":
            setattr(clientbound, n.name, new_packet)
            id_map.append((n.args[0], getattr(clientbound, n.name)))

        elif i.name == "twoway":
            setattr(twoway, n.name, new_packet)
            id_map.append((n.args[0], getattr(twoway, n.name)))

        # From another script, we can access e.g. packets.serverbound.connect.id and get 0x4002

id_dict = dict(id_map)

def decode(packet: bytes):
    """Decode packet"""
    # Start by getting the header values and verifying them
    length = int.from_bytes(packet[0:4])
    if length != len(packet):
        raise PacketReadError(f"Mismatched packet length (expected {length}, got {len(packet)})")

    mv = int.from_bytes(packet[4:6])
    if mv != VERSION_MAJOR:
        raise PacketReadError(f"Mismatched packet major version (we're on v{VERSION_MAJOR}.{VERSION_MINOR}, packet's on v{mv})")

    packet_id = int.from_bytes(packet[8:10])

    packet_cls = id_dict[packet_id] # Create a new Packet class instance

    i = 10
    if 'i' in packet_cls.flags:
        packet_cls.idempotency = packet_cls[10:14]
        i += 4

    # Populate the packet class
    for fname, ftype in packet_cls.fields.items(): # fname = name of the packet field, ftype = data type of the field as defined in data_types.py
        fcls, inc = getattr(dt, ftype).decode(packet[i:]) # returns a tuple (data type class, number of bytes read from input)
        setattr(packet_cls, fname, fcls)

        i += inc

    return packet_cls

def encode(packet: Packet):
    """Encode a Packet"""
    # First, we need to construct the packet fields, then put together the header
    pkt_fields = bytes()
    for i in packet.fields:
        pkt_fields += getattr(packet, i).encode() # Encode the field into bytes and add to the end of pkt_fields
        # getattr(packet, i) is essentially the same as packet.i where i is the name of the attribute

    header_fields = [dt.uint16(VERSION_MAJOR), dt.uint16(VERSION_MINOR), dt.uint16(packet.id)]
    if 'i' in packet.flags:
        header_fields.append(packet.idempotency)

    # Finally, construct the packet
    encoded_pkt = bytes()
    for i in header_fields:
        encoded_pkt += i.encode()

    encoded_pkt += pkt_fields

    # Insert the final packet size
    size = dt.uint32(len(encoded_pkt) + 4).encode()
    return size + encoded_pkt

if __name__ == "__main__":
    # Example packet
    my_packet = clientbound.recieve_message()
    my_packet.nickname = dt.lds("Lascode")
    my_packet.content = dt.nts("I am a very cute kitty")

    my_encoded_packet = encode(my_packet)

    print(my_encoded_packet) # send out to client

    my_decoded_packet = decode(my_encoded_packet)

    print(f"{my_decoded_packet.nickname}: {my_decoded_packet.content}") # my_decoded_packet is a recieve_message packet
