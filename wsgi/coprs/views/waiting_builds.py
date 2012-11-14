import flask

from coprs import db
from coprs import models

waiting_builds_ns = flask.Blueprint('waiting_builds', __name__, url_prefix = '/waiting_builds')

@waiting_builds_ns.route('/')
def waiting_builds():
    query = db.session.query(models.Build, models.Copr, models.User).\
                        join(models.Build.copr).\
                        join(models.Copr.owner).\
                        filter(models.Build.started_on == None).\
                        filter(models.Build.canceled != True).\
                        order_by(models.Build.submitted_on.asc())[0:10]

    builds = map(lambda x: x[0], query)
    return flask.jsonify({'builds': [build.to_dict(options = {'copr': {'owner': {'__columns_except__': ['openid_name', 'proven'] },
                                                                       '__columns_except__': ['chroots', 'repos'],
                                                                       '__included_ids__': False},
                                                              '__included_ids__': False}) for build in builds]})
