'''
Created on 26-Dec-2011

@author: Kushal
'''
from vcweb import settings
from neo4j import GraphDatabase
from neo4j import OUTGOING,ANY
from neo4j import Evaluation

import atexit
import time

import logging
logger = logging.getLogger(__name__)

class Enum(set):
    def __init__(self, *args, **kwargs):
        super(Enum, self).__init__(args, **kwargs)
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError("No enum value %s" % name)
    def values(self):
        return self
    def all(self):
        return self

Index = Enum('PARTICIPANT', 'ACTIVITY', 'COMMENT')
RelationshipIndex = Enum('TAGS')
Relationship = Enum('LIKE','COMMENT','PERFORMS')

class Neo4jDAO(object):
    '''
    Sample Singleton implementation
    '''
    _instance = None
    _db = GraphDatabase(settings.GRAPH_DATABASE_PATH)
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Neo4jDAO, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    def create_node_index(self,index):
        with self._db.transaction:
            idx = self._db.node.indexes.create(index)
        return idx
    def create_rel_index(self,index):
        with self._db.transaction:
            idx = self._db.relationship.indexes.create(index)
        return idx
    def get_node_index(self,index):
        with self._db.transaction:
            idx = self._db.node.indexes.get(index)
        return idx
    def get_rel_index(self,index):
        with self._db.transaction:
            idx = self._db.relationship.indexes.get(index)
        return idx

    def shutdown(self):
        logger.debug("Shutting down neo4j embedded database")
        try:
            self._db.shutdown()
        except NameError:
            print 'Could not shutdown Neo4j database. Is it open in another process?'
    
    def initialize_indexes(self):
        try:
            logger.debug("creating indexes for %s and relationship indexes %s", Index, RelationshipIndex)
            for index in Index.values():
                #FIXME: Work around to avoid re-creation of index at time of unit testing 
                #       as post_syncdb method is invoked every time for 'manage.py test'
                if self.get_node_index(index) is not None:
                    logger.debug("Index %s already exists for nodes", index)
                    continue
                self.create_node_index(index)
            for relationship_index in RelationshipIndex.values():
                #FIXME: Work around to avoid re-creation of index at time of unit testing 
                #       as post_syncdb method is invoked every time for 'manage.py test'
                if self.get_rel_index(relationship_index) is not None:
                    logger.debug("Index %s already exists for relationship", relationship_index)
                    continue
                self.create_rel_index(relationship_index)
        except Exception as e:
            logger.debug("Unable to initialize indexes: %s", e)

dao = Neo4jDAO()
# FIXME: do not expose _conn here, all access should go through dao instead
_conn = dao._db

class Activity(object):
    def __init__(self):
        self._pid = None
        self._name = None
        self._nodetype = "activity"
        self._participant = None
    
    
    @property
    def participant(self):
        return self._participant
    
    @participant.setter
    def participant(self,obj):
        self._participant = obj
        
    @property
    def pid(self):
        return self._pid
    
    @pid.setter
    def pid(self,value):
        self._pid = value
        
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self,value):
        self._name = value
    
    @property
    def nodetype(self):
        return self._nodetype

class Participant(object):
    def __init__(self):
        self._pid = None
        self._username = None
        self._nodetype = "participant"
    
    @property
    def pid(self):
        return self._pid
    
    @pid.setter
    def pid(self,value):
        self._pid = value
        
    @property
    def username(self):
        return self._name
    
    @username.setter
    def username(self,value):
        self._name = value
    
    @property
    def nodetype(self):
        return self._nodetype
    
class Comment(object):
    
    def __init__(self):
        self._text = None
        self._tag = None
        self._type = "comment"
        self._participant = None
    @property
    def text(self):
        return self._text
    
    @text.setter
    def text(self,value):
        self._text = value
    
    @property
    def tag(self):
        return self._tag
    
    @tag.setter
    def tag(self,value):
        self._tag = value
            
    @property
    def participant(self):
        return self._participant
    
    @participant.setter
    def participant(self,obj):
        self._participant = obj
    
    
def create_participant(pk,username):
    if get_participant(pk) is not None:
        raise ValueError("Participant Node of id %s already exists." % pk)
    with _conn.transaction:
        participant = _conn.node(id=pk,username=username,type="participant")
        dao.get_node_index(Index.PARTICIPANT)['username'][username] = participant
        dao.get_node_index(Index.PARTICIPANT)['id'][pk] = participant
    return participant

def create_activity(pk,name):
    if get_activity(pk) is not None:
        raise ValueError("Activity Node of id %s already exists." % pk)
    with _conn.transaction:
        activity = _conn.node(id=pk,name=name,type="activity")
        dao.get_node_index(Index.ACTIVITY)['name'][name] = activity
        dao.get_node_index(Index.ACTIVITY)['id'][pk] = activity
    return activity

#creates comment node
#param:pk = unique token of activity performed by participant
#param: text = actual comment
def create_comment(ppk,activity_performed_id,text):
    with _conn.transaction:
        comment = _conn.node(tag=activity_performed_id,text=text,type="comment")
        dao.get_node_index(Index.COMMENT)['tag'][activity_performed_id] = comment
    create_participant_comment_rel(ppk,comment,RelationshipIndex.TAGS)
    return comment    

#create participant activity relationship
#param : apk = activity id
#param : ppk = participant id
#param : reltype = relationship type
#relationship properties: unique tag,timestamp
def create_participant_activity_rel(apk,ppk,reltype):
    activity_node = get_activity(apk)
    participant_node = get_participant(ppk)
    create_time = long(time.time())
    activity_performed_id = ''.join([apk,ppk,str(create_time)])
    print str(create_time) + " " + str(activity_performed_id)
    with _conn.transaction:
        participant_node.relationships.create(reltype,activity_node,timestamp=create_time,tag=activity_performed_id)
    #TODO:return activity perform id after successful creation
    pass

#create participant comment relationship
#param : ppk = participant id
#param : obj = comment node obj
def create_participant_comment_rel(ppk,comment,reltype):
    participant_node = get_participant(ppk)
    create_time = time.time()
    with _conn.transaction:
        comment.relationships.create(reltype,participant_node,timestamp=create_time,notification_flag=False)
    pass

def get_participant(pk):
    return dao.get_node_index(Index.PARTICIPANT)['id'][pk].single

def get_activity(pk):
    return dao.get_node_index(Index.ACTIVITY)['id'][pk].single

def get_comment(tag):
    return dao.get_node_index(Index.COMMENT)['tag'][tag]

def node_evaluator(path):
    
    return

def wall_page(ppk):
    wall_thread_list = []
    participant_obj = get_participant(ppk)
    if participant_obj is None:
        raise Exception("Participant of id %s not found.",ppk)
    traverser = _conn.traversal().relationships(Relationship.PERFORMS,OUTGOING).traverse(participant_obj)
    #obtain all activity performed by the current participant
    
    count = 0
    for path in traverser:
        wall_thread_dict={}
        #each instance of item consists of start node,relationship & end node
        #the first item will be the start node, the second will be the first relationship, 
        #the third the node that the relationship led to and so on.
        #print path
        #TODO: To handle when path=0 i.e. USE_CASE: When participant only comments and doesn't perform activity
        if count ==0:
            count=count+1
            continue
        participant_node = path.start
        activity_node = path.end
        
        performed_activity = Activity()
        performed_participant = Participant()
        
        for activityKey in activity_node.propertyKeys:
            setattr(performed_activity, activityKey, activity_node[activityKey])
            
        for participantKey in participant_node.propertyKeys:
            setattr(performed_participant, participantKey, participant_node[participantKey])
            
        performed_activity._participant = performed_participant
        wall_thread_dict["activity_detail"] = performed_activity
        list_comment = []
        for rel in path.relationships:
            #if a relationship - obtain tag and find all comment node corresponding to that tag with help of index
            #else if a node - check for node type(i.e. activity node). 
            #from this node movie one step for LIKE relationship and obtain all participant
            tag = rel['tag']
            #print "tag of the activity:",tag
            comments_node = get_comment(tag)
            if comments_node==0:
                break
            for comment in comments_node:
                print "for activity with tag: {0} , comment is: {1}".format(tag,comment['text'])
                c = Comment()
                
                for comment_key in comment.propertyKeys:
                    setattr(c, comment_key, comment[comment_key])
                
                comment_traverser = _conn.traversal().relationships(Relationship.COMMENT,OUTGOING).traverse(comment)
                counter = 0
                for node in comment_traverser.nodes:
                    
                    if count == 0:
                        counter=counter+1
                        continue
                    
                    participant_commented = Participant()
                    if node.hasProperty("username"):
                        for propertyKey in node.propertyKeys:
                            setattr(participant_commented, propertyKey, node[propertyKey])
                    c._participant = participant_commented
                list_comment.append(c)
        wall_thread_dict["comments_details"] = list_comment
        print wall_thread_dict

atexit.register(dao.shutdown)
    
if __name__ == '__main__':
    """
    usernames = []
    for i in range(1,10):
            username = 'test'+str(i)+'@asu.edu'
            usernames.append(username)
            create_participant(i, username)
    """
    print get_participant(1)
    
    dao.shutdown()
