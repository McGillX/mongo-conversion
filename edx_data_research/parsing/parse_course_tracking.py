'''
This module will extract tracking logs for a given course and date range
between when course enrollment start and when the course ended. For each log,
the parent_data and meta_data from the course_structure collection will be 
appended to the log based on the event key in the log
'''
import json

from datetime import datetime

from edx_data_research.parsing.parse import Parse


class CourseTracking(Parse):

    def __init__(self, args):
        super(CourseTracking, self).__init__(args)
        self.collections = ['tracking', 'course_structure']
        self.course_config_file = args.course_config_file
        self.drop = args.drop
        # We need reference to the tracking collection from the main tracking
        # database
        self.tracking_tracking = self.client['tracking']['tracking']

    def migrate(self):
        if self.drop:
            self.collections['tracking'].drop()
        course_ids, start_date, end_date = self._load_config_file(
                                               self.course_config_file)
        self._extract_tracking_logs(course_ids, start_date, end_date)

    def _load_config_file(self, course_config_file):
        '''
        Return course ids and ranges of dates from which course specific
        tracking logs will be extracted
        '''
        with open(course_config_file) as file_handler:
            data = json.load(file_handler)
        if not isinstance(data['course_ids'], list):
            raise TypeError('Expecting list of course ids')
        try:
            start_date = datetime.strptime(data['date_of_course_enrollment'],
                                           '%Y-%m-%d')
            end_date = datetime.strptime(data['date_of_course_completion'],
                                         '%Y-%m-%d')
        except ValueError:
            raise ValueError('Incorrect data format, should be YYYY-MM-DD')
        return data['course_ids'], start_date.date(), end_date.date()

    def _append_course_structure_data(self, course_structure_collection, _id):
        '''
        Append parent_data and metadata (if exists) from course structure to 
        tracking log
        '''
        output = {}
        data = course_structure_collection.find({"_id" : _id})
        if data is None:
            data = course_structure_collection.find({'_id': {'$regex': _id}})
        if 'parent_data' in data:
            output['parent_data'] = data['parent_data']
        if 'metadata' in data:
            output['metadata'] = data['metadata']
        return output

    def _extract_tracking_logs(self, course_ids, start_date, end_date):
        '''
        Return all trackings logs that contain given ids and that contain dates
        within the given range
        '''
        start_date = start_date.isoformat()
        end_date = end_date.isoformat()
        query = {'course_id' : {'$in' : course_ids}, 'time':
                 {'$gte': start_date, '$lte': end_date}}
        documents = self.tracking_tracking.find(query)
        for document in documents:
            exists = (self.collections['tracking'].find({'_id': document['_id']})
                      .limit(1))
            if not exists.count(True):
                # Bind parent_data and metadata from course_structure to
                # tracking document
                #if document['event_type'] != 'page_close':
                #    bound = False
                #    if document['event']:
                #        if isinstance(document['event'], dict):
                #            if 'id' in document['event']:
                #                splitted = document['event']['id'].split('-')
                #                if len(splitted) > 3:
                #                    document['event']['id'] = splitted[-1]
                #                    if not bound:
                #                        document.update(
                #                            self._append_course_structure_data(
                #                            self.collections['course_structure'],
                #                            document['event']['id']))
                #                        bound = True
                #    if document['page']:
                #        splitted = document['page'].split('/')
                #        if len(splitted) > 2:
                #            document['page'] = splitted[-2]
                #            if not bound:
                #                document.update(
                #                    self._append_course_structure_data(
                #                    self.collections['course_structure'],
                #                    document['page']))
                # End of binding, now insert document into collection
                self.collections['tracking'].insert(document)
