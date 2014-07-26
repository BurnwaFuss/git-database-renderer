"""
 Copyright (C) 2014 the original author or authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.


@author: Barry Weinstein
"""

import re

fontsizenode = 12
fontsizeedge = 12

def listAtDictKeyAppend(dictionary, key, value):
    """Convenience method to add an object to a list at a dictionary's key"""
    if key in dictionary:
        dictionary[key].append(value)
    else:
        newlist = [value]
        dictionary[key] = newlist

def newFrom(objtype, objhsh, prettylines, headnames):
    """Factory method to construct a concrete instance of Dbobj having type objtype"""
    
    if objtype == 'tag':
        return Tag(objtype, objhsh, prettylines)
    elif objtype == 'commit':
        return Commit(objtype, objhsh, prettylines, headnames)
    elif objtype == 'tree':
        return Tree(objtype, objhsh, prettylines)
    elif objtype == 'blob':
        return Blob(objtype, objhsh, prettylines)
    else:
        raise Exception("unknown object type - " + objtype)

def part(line, idx):
    """Convenience language to return a part of a line after it's split at whitespace"""
    parts = re.split("\s", line)
    if idx >= len(parts):
        return None
    return parts[idx]

def q(astring):
    """Convenience language to return astring surrounded by quotes"""
    return "\"" + astring + "\""

def wl(f, string):
    f.write(string + "\n")

class Dbobj(object):
    """Any database object"""
    
    def __init__(self, objtype, objhsh, prettylines):
        # a dictionary of hashes to Refs interpreted from my prettylines
        self.references = {}
        # a rename without content change will be the same blob. The two different
        # containing tree-ish's will reference the blob by different names
        self.referencedbynames = set()
        # provided by Dag
        self.objsReferring2Me = []
        self.objsIReference = []

        self.objtype = objtype
        self.objhsh = objhsh
        self.prettylines = prettylines      
    def noticeReference(self, ref):
        """Notice my reference during construction"""
        # The very same object can be referenced more than
        # once if that object represents two different real files or directories
        # that happen to hash the same.
        if ref.hsh in self.references.keys():
            self.references[ref.hsh].append(ref)
        else:
            self.references[ref.hsh] = [ref]
    def acceptReferenced(self, dbobj):
        """Accept that I reference dbobj since the DAG told me so"""
        self.objsIReference.append(dbobj)
    def acceptReferrer(self, dbobj):
        """Accept that dbobj refers to me since the DAG told me so"""
        self.objsReferring2Me.append(dbobj) 
    def present(self):
            print("****\n" + self.objtype + " " + self.objhsh)
    def dotDescribe(self):
        return q(self.id()) + self.dotAttr()
    def id(self):
        return self.objhsh[0:6]
    def dotAttr(self):
        color = "color=grey"
        label = str(self.id())
        headnames = None
        if self.objtype == 'commit':
            color = "color=red"
            if len(self.headnames) > 0:
                headnames = "-".join(self.headnames)
                label = headnames + "\\n" + label;
        elif self.objtype == 'tree':
            color = "color=green"
        elif self.objtype == 'tag':
            color = "color=blue"
        elif self.objtype == 'blob':
            color = "color=grey"
        attrs = color  + ";label="  + q(label) + "fontsize=" +  str(fontsizenode)
        return "[" + attrs +  "]"
        
           
class Tag(Dbobj):
    """A subclass of Dbobj abstracting a tag in a Git repository"""

    def __init__(self, objtype, objhsh, prettylines):
        super(Tag, self).__init__(objtype, objhsh, prettylines)
        for line in prettylines:
            part0 = part(line, 0)
            if part0 == 'tag':
                self.label = part(line, 1)
            if part0 == 'object':
                objhash = part(line, 1)
                self.noticeReference(Ref(objhash))
    def present(self):
            super(Tag, self).present()
            print("-> " + self.prettylines[1]) 
            print("-> " + self.prettylines[2]) 
    
class Commit(Dbobj):
    """A subclass of Dbobj abstracting a commit in a Git repository"""


    def __init__(self, objtype, objhsh, prettylines, headnames):
        self.headnames = []
        if headnames:
            for headname in headnames:
                self.headnames.append(headname)
        super(Commit, self).__init__(objtype, objhsh, prettylines)
        for line in prettylines:
            part0 = part(line, 0)
            if part0 == 'parent' or part0 == 'tree':
                objhash = part(line, 1)
                self.noticeReference(Ref(objhash))
                
    def present(self):
        """Send to stdout a textual representation of this object"""

        super(Commit, self).present()
        print("-> " + self.prettylines[0])
        print("-> " + self.prettylines[1])
        readyforcomment = False 
        for linenum in range(2, len(self.prettylines)):
            if readyforcomment:
                print(self.prettylines[linenum])
                continue
            if len(self.prettylines[linenum]) == 0:
                readyforcomment = True

class Tree(Dbobj):
    """A subclass of Dbobj abstracting a directory version in a Git repository"""

    def __init__(self, objtype, objhsh, prettylines):
        super(Tree, self).__init__(objtype, objhsh, prettylines)
        for line in prettylines:
            part1 = part(line, 1)
            if part1 == 'blob' or part1 == 'tree':
                objhash = part(line, 2)
                referencedbyname = part(line, 3)
                self.noticeReference(Ref(objhash, referencedbyname))
    def present(self):
        """Send to stdout a textual representation of this object"""

        super(Tree, self).present()
        if len(self.referencedbynames) > 0:
            print("known as " + str(self.referencedbynames))
        else:
            print("root tree")
        for line in self.prettylines:
            if len(line) == 0:
                continue
            print("-> " + line)
            
class Blob(Dbobj):
    """A subclass of Dbobj abstracting a file versioned in a Git repository"""
    
    def __init__(self, objtype, objhsh, prettylines):
        super(Blob, self).__init__(objtype, objhsh, prettylines)
        self.content = prettylines
    
    def present(self):
        """Send to stdout a textual representation of this object"""

        super(Blob,self).present()
        print("known as " + str(self.referencedbynames));
        print("-> first line: " + self.prettylines[0])

class Ref(object):
    """An abstraction of a relationship between two objects in the object database
    
    This is introduced hold the various names that database objects are referred to.
    """
    
    def __init__(self, hsh, referencedbyname=None):
        self.hsh = hsh
        self.nameused = referencedbyname

class Dag(object):
    """Graph of database object relationships"""
    
    def __init__(self, dbobjs):
        self.edges = []
        self.edgesfrom = {}
        self.edgesto= {}
        self.dbobjs = dbobjs
        for referrer in dbobjs:
            for referenced in dbobjs:
                if referenced.objhsh in referrer.references.keys():
                    referrer.acceptReferenced(referenced)
                    referenced.acceptReferrer(referrer)
                    edgerefs= []
                    # There might be multiple references between these two
                    # objects if there are two things that hash
                    # to the same referenced blob
                    for ref in referrer.references[referenced.objhsh]:
                        edgerefs.append(ref)
                        referenced.referencedbynames.add(ref.nameused)
                    edge = Edge(referrer, referenced, edgerefs)
                    self.edges.append(edge)
                    self.edgesfrom[referrer] = edge
                    self.edgesto[referenced] = edge
    
    def dotDescribe(self, outfile):
        """Send to outfile DOT language instructions to render this entire DAG"""
        
        dot = None
        try:
            if outfile:
                dot = open(outfile, 'w+')
            else:
                dot = open("/Users/bweinste/Desktop/git.dot", 'w+')
            self.dotDescribeToFile(dot)
        finally:
#             dot.close()
            pass
            
    def dotDescribeToFile(self, dot):
        wl(dot, "digraph graphname {")
        for dbobj in self.dbobjs:
            wl(dot, dbobj.dotDescribe())
        for edge in self.edges:
            wl(dot, edge.dotDescribe())
        wl(dot, "}")

class Edge(object):
    """A directed edge of an acyclic graph"""
    def __init__(self, beginning, ending, edgerefs):
        self.beginning = beginning
        self.ending = ending
        if not edgerefs or len(edgerefs) == 0:
            self.referencename = 'anonymous'
        else:
            refnames = []
            for ref in edgerefs:
                if ref.nameused:
                    refnames.append(ref.nameused)
            self.referencename = '-'.join(refnames)
    
    def dotDescribe(self):
        """Return a DOT language representation of this edge"""
        label = ""
        nm = self.referencename
        if nm != 'anonymous':
            label = " [label=\"" + nm +  "\"; fontsize=" + str(fontsizeedge) + "]"
        beginning = q(self.beginning.id())
        ending = q(self.ending.id())
        return(beginning + " -> " + ending + label + ";")
