#!/usr/bin/env python
# encoding: utf-8

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


@author:     Barry Weinstein
"""

import sys
import os
import subprocess
import dbobject
from dbobject import  Dag
from optparse import OptionParser

gitdir = None
objdir = None
tagsdir = None
hash2obj = {}

def error(err):
    """Report an error to stdout
    
    This is a function supplied to the walk of the object database directory structure.
    """
    print("got an error" + str(err))

def collectFromAnchors():
    """Gather all objects recursively reachable from the tags and commits as determined by the inter-database references
    """
    gatherTags()
    for objhash in allCommitHashes():
        descend(objhash)
        
def descend(objhash):
    """Recursive depth-first traversal of the object database as determined by their inter-database references
    
    Each object encountered is added to the hash2obj dictionary. The descent is cut short if the object is already
    present.
    """
    if objhash in hash2obj.keys():
        return
    newobj = objFromHash(objhash)
    hash2obj[objhash] = newobj
    for objhash in newobj.references.keys():
        if not objhash in hash2obj.keys():
            descend(objhash)
            
def objFromHash(objhash):
    """Construct an instance of a subclass of dbobject.Dbobj corresponding to the objhash parameter"""
    objtype = subprocess.check_output(['git', '--git-dir=' + gitdir, 'cat-file', '-t', objhash])
    asPretty = subprocess.check_output(['git', '--git-dir=' + gitdir, 'cat-file', '-p', objhash])
    objtype = objtype.split('\n')[0]
    prettylines = asPretty.split('\n')
    return dbobject.newFrom(objtype, objhash, prettylines)

def allCommitHashes():
    """ Return the hashes of every commit in the repository"""
    allhashesline = subprocess.check_output(['git', '--git-dir=' + gitdir, 'log', '--format=%H'])
    allhashes = allhashesline.split('\n')
    return allhashes[0:-1]
       
def gatherTags():
    """Add all tag objects into the dictionary hash2obj for the tag references found in the repository""" 
    for tagfile in os.listdir(tagsdir):
        tagfilepath = os.path.join(tagsdir, tagfile)
        with open(tagfilepath) as f:
            line = f.read()
            hashoftag = line[0:-1]
            hash2obj[hashoftag] = objFromHash(hashoftag)

def collectFromObjs():
    """Add every object found in the database's file structure to the hash2obj dictionary
    """
    for root, dirs, names in os.walk(objdir, topdown=True, onerror=error):
        if 'info' in dirs:
            dirs.remove('info')
        if 'pack' in dirs:
            # guess we should actually expand the pack but not for now.
            dirs.remove('pack')
        containernm = os.path.split(root)[1];
        for objname in names:
            objhash = (containernm + objname)
            if objhash not in hash2obj.keys():
                newobj = objFromHash(objhash)
                hash2obj[objhash] = newobj
 
def analyzeObjectDatabase(repodir, graphoutputfile=None):
    """Send to stdout the objects in the database and produce a graphical representation
    """
    global gitdir, objdir, tagsdir
    gitdir = os.path.join(repodir, '.git')
    objdir = os.path.join(gitdir,'objects')
    tagsdir = os.path.join(gitdir, 'refs', 'tags')

    # collect all objects into the hash2obj global dictionary
    collectFromAnchors()
    collectFromObjs()
    allobjs = hash2obj.values()
    # create a directed acyclic graph
    dag = Dag(allobjs)
    # send the objects to stdout
    for dbobj in allobjs:
        dbobj.present()
    # create the file containing the graph in dot notation
    if graphoutputfile:
        outfile = graphoutputfile
    else:
        outfile = os.path.join(os.environ['HOME'], 'git.dot')
    dag.dotDescribe(outfile)
 
 
if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-o', '--out', dest='outfile', help="set output path of dot file", metavar='FILE')
 
    (opts, args) = parser.parse_args(sys.argv)
    if len(args) == 2:
        repodir = args[1]
        analyzeObjectDatabase(repodir, opts.outfile)
        sys.exit()
    else:
        print("just run this program with the path of a git repository as an argument")
        sys.exit(1)
    
