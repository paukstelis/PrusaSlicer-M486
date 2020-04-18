#!/usr/bin/python3
import sys
import re
import os

startregex = re.compile("; printing object (.*) id:(\d+) copy (\d+)")
endregex = re.compile("; stop printing object (.*) id:(\d+) copy (\d+)")

sourcegcode=sys.argv[1]

objects = []
oindex = 0

# stolen directly from filaswitch, https://github.com/spegelius/filaswitch
class Gcode_parser:
    MOVE_RE = re.compile("^G0\s+|^G1\s+")
    X_COORD_RE = re.compile(".*\s+X([-]*\d+\.*\d*)")
    Y_COORD_RE = re.compile(".*\s+Y([-]*\d+\.*\d*)")
    E_COORD_RE = re.compile(".*\s+E([-]*\d+\.*\d*)")
    Z_COORD_RE = re.compile(".*\s+Z([-]*\d+\.*\d*)")
    SPEED_VAL_RE = re.compile(".*\s+F(\d+\.*\d*)")

    def __init__(self):
        self.last_match = None

    def is_extrusion_move(self, line):
        """
        Match given line against extrusion move regex
        :param line: g-code line
        :return: None or tuple with X, Y and E positions
        """
        self.last_match = None
        m = self.parse_move_args(line)
        if m and (m[0] is not None or m[1] is not None) and m[3] is not None and m[3] != 0:
            self.last_match = m
        return self.last_match

    def parse_move_args(self, line):

        self.last_match = None
        m = self.MOVE_RE.match(line)
        if m:
            x = None
            y = None
            z = None
            e = None
            speed = None

            m = self.X_COORD_RE.match(line)
            if m:
                x = float(m.groups()[0])

            m = self.Y_COORD_RE.match(line)
            if m:
                y = float(m.groups()[0])

            m = self.Z_COORD_RE.match(line)
            if m:
                z = float(m.groups()[0])

            m = self.E_COORD_RE.match(line)
            if m:
                e = float(m.groups()[0])

            m = self.SPEED_VAL_RE.match(line)
            if m:
                speed = float(m.groups()[0])

            return x, y, z, e, speed


parser = Gcode_parser()

def _get_entry(oid,copy,oindex):
    for o in objects:
        if o["id"] == oid and o["copy"] == copy:
            return o["index"],oindex
    objects.append({"id" : oid, "copy" : copy, "index" : oindex})
    oindex += 1
    return objects[-1]["index"],oindex

with open(sourcegcode, 'r+') as fd:
    contents = fd.readlines()
    gcodelines = enumerate(contents)
    obj_startline = None
    e_distance = None
    tracking = False

    for index, line in gcodelines:

        #Are we going to track extrusions?
        if line.startswith("M83"):
           tracking = True

        if obj_startline and tracking:
           #track extrusions
           eaction = parser.parse_move_args(line)
           if eaction and eaction[3]:
              e_distance = eaction[3]

        startmatch = startregex.match(line)
        if startmatch:
           obj_index, oindex = _get_entry(startmatch.group(2),startmatch.group(3),oindex)
           obj_startline = index
           #contents.insert(index + 1, "M486 S{0}\n".format(obj_index))
        endmatch = endregex.match(line)
        if endmatch:
           obj_endline = index
           line_diff = obj_endline - obj_startline
           #print(line_diff)
           #how to move this conditional to one liner?
           if tracking:
              contents.insert(obj_endline+1, "M486 S-1 E{0}\n".format(e_distance))
           else:
              contents.insert(obj_endline+1, "M486 S-1\n")

           contents.insert(obj_startline+1, "M486 S{0} O{1}\n".format(obj_index,line_diff))
           obj_endline = None
           obj_startline = None
           e_distance = None
           for _ in range(2):  # skip 2
              next(gcodelines, None)

    contents.insert(0,"M486 T{0}\n".format(len(objects)))
    fd.seek(0)
    fd.writelines(contents)



       
