# Chat Protocol Format

### The following network packet format is designed to be simple, while also building in some future-proofing.

## Types of packets

A packet is a string of bytes containing information about a chat message or a server event e.g. a person joining.\
Packets can either be server-bound, client-bound or two-way.\
Examples:

**Server-bound:** 'Send Message' packet containing at least an authorisation token and the message content

**Client-bound:** 'Recieve Message' packet from the server containing a message and the ID of the user who sent it

**Two-way:** 'Response' packet which signals whether an action succeeded or failed

## Packet header

All packets have the same string of bytes at the start of the packet to identify its length, version number, type etc.\
Note that if the field is an unsigned integer (uint*), a byte count of 1 allows for a value of up to 255, 2 bytes up to 65,535, and 3 bytes 16,777,215.

| No. of bytes | Name | Type | Description |
| - | --------------- | ---- | ----------- |
| 4 | Packet length   | uint | The total length of the packet in bytes |
| 2 | Major version   | uint | The major version number. See below for info. |
| 2 | Minor version   | uint | The minor version number |
| 2 | Packet type     | uint | The ID of the packet |
| 0/4 | Idempotency   | uint | See: [Idempotency](#Idempotency) |
| 0/n | Authorisation | -    | See: [Authorisation](#Authorisation) |

## Version number
A version number is made of 2 values, major and minor.\
Every time a new update is released the minor value is incremented.\
If the update is not compatible with older clients/servers (e.g. a new client connecting to an old server would break) then the minor version is set to 1 and
the major value is incremented.

A major version value of 0 assumes a debug scenario where version numbers are not an issue and all clients/servers are compatible.

Don't worry about this for now, just set both versions to 0 since we are not currently planning to release the software. This is just for future-proofing.

## Idempotency
This is a unique key that is used to prevent actions from being repeated.

For example, if the client sends a message to the server and the server does not respond, the client may attempt to send the message again, assuming the server did not recieve the original one.

However, there are cases where the server successfully recieved the message but the connection is interrupted before the client recieves the response.\
In this case, the client will try to send the message again, and in doing so create a duplicate message on the server.

To prevent this, a unique token is generated when the user sends a message to make the request 'idempotent'. This same token is used when the client attempts to re-send the message. If the server recieves a request with the same idempotency token as a previous request, it will be ignored.

Our idempotency token is the number of milliseconds since the start of the day. In reality it can be anything random. We are building in the assumptions here that the client will not attempt to re-send the request after 24 hours, nor will it send 2 requests in the same millisecond. These are considerations for real platforms such as Discord, however we can ignore this for now.

The Idempotency field in the packet header will only be included if the packet type is non-idempotent. It is not needed for a request to retrieve information from the server for example.

## Authorisation
**TODO:** Don't worry about this now, we can include this if we want to do account registration in a future date

The Authorisation field in the packet header will only be included if the packet 'requires authorisation'. No packet should include this for now since we are not doing authorisation yet.

## Data types
These are pre-defined data types used in fields. Each byte in the examples is a value wrapped in square brackets.\
If the value starts with '#', it is a hexadecimal value ('#F2'), otherwise it is an ASCII character ('A') or expression ('NUL').

| ID | Name | Example | Note
| -- | ---- | ------- | ----
| uint8 | Unsigned 8-bit integer | [#A7]
| uint16/24/32 etc | Unsigned integer | [#12] [#3A] [#45] ...
| sint8/16/24 etc | Signed integer | [#80] [#FF] [#12] ... | First bit determines whether it is negative
| ldi | Length-determined integer | [#04] [#12] [#3A] [#45] [#6C] | First byte is a 7-bit uint which represents the length in bytes. If length is 0, consider the value to be 0. If first bit of length is 1, treat value as a negative signed int.
| nts | Null-terminated string | [H] [E] [L] [L] [O] [NUL] | Arbitary length string ending in 'NUL' (0x00)
| lds | Length-determined string | [#05] [H] [E] [L] [L] [O] | Maximum length of 255

## Length handling
On recieving a packet, if there are more fields than expected, ignore them. This is in case additional fields are added in a later update.

If the packet has a different length than given in the 'Packet length' header, drop it.\
**TODO:** Decide whether an error response should be sent

# Python Implementation
Using the packet encoding/decoding system is fairly simple. I'd recommend taking a look at `/res/util/packets.kdl` and the example at the end of `packets.py`.

To construct a packet, you first need to check that you've imported the data types file at the start of your program:\
`import util.data_types as dt` # -- (you're not using datetime, right?)

Then call `my_packet = dt.clientbound.packet_name()`.
If you're sending a server-bound or two-way packet, use `serverbound` and `twoway` respectively.

To populate the packet, fill each attribute with their required data type from data_types.py.\
`my_packet.content = nts("Hello, world!")`\
`my_packet.whatever_number = uint16(1234)`\
**TODO:** I have an idea on how to make nts() etc. obsolete, but I can't be bothered right now. Consider it deprecated after v1

Then to encode the packet:\
`dt.encode(my_packet)`\
This will encode the packet into a string of bytes ready to be sent.

To decode a string of bytes into a packet:\
`my_packet = dt.decode(encoded_packet)`

To access an attribute:\
`message = str(my_packet.content)`

# Packet identifiers
Okay, that was a huge amount of what is essentially boiler-plate documentation. For our application, there's no way packets need to be this complex, but it's really fun to learn about.

**Packet flags:**\
non-**i**dempotent = requires idempotency token (only needed if -r is also set)\
**a**uthorised = requires authorisation\
**r**esponse = requres a response [0000]

## Server-bound [4xxx]

### [4001] Send message -ri
| Type | Name | Description
| ---- | ---- | -----
| nts | Content | The message content

### [4002] Connect -ri
| Type | Name | Description
| ---- | ---- | -----
| lds | Nickname | nickname of user

### [4003] Change nickname -ri
| Type | Name | Description
| ---- | ---- | -----
| lds | Nickname | new nickname

### [4004] Disconnect
| Type | Name | Description
| ---- | ---- | -----
| lds | Reason | Reason for disconnect

## Client-bound [8xxx]

### [8000] Keep Alive -r
Asks the client if it is still connected

### [8001] Recieve Message
| Type | Name | Description
| ---- | ---- | -----
| lds | Nickname | nickname of user sending the message
| nts | Content | Message content

### [8002] Connect
| Type | Name | Description
| ---- | ---- | -----
| lds | Nickname | nickname of user that joined
| lds | Message | welcome message

### [8003] Change nickname
| Type | Name | Description
| ---- | ---- | -----
| lds | Old nickname | The user who changed their nick
| lds | Nickname | User's new nickname

### [8004] Disconnect
| Type | Name | Description
| ---- | ---- | -----
| lds | Nickname | Nickname of user who left
| lds | Message | Reason for disconnect


## Two-way [0xxx]

### [0000] Response
Signals whether the request succeeded
| Type  | Name | Description
| ----- | ---- | -----
| uint8 | Value | 0 if successful, otherwise error code
| nts | Content | The text response or error message
