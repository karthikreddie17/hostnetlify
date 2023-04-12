from flask_restful import Api, Resource, reqparse
from db1 import *

api=Api()  #Api(app) is cannot be written because everything is not in same module
#because sqlalchemy and app are defined in another models so use __init__


class Api_Venues(Resource):
    #def get() it is a class method so write so write self
    def get(self):

        #d1 is the list of al venues output of api is jsonfile
        all_venues={} #{"id":"<venue_name>"}
        d1=Venues.query.all()
        for ven in d1:
            #venue id as key and venue name as value
            all_venues[ven.venue_id] = ven.venue_name
        return all_venues
        #return in app.py 1)render template endpoint retrun html page
        #API returing some json file

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str, required=True)
        parser.add_argument("location", type=str, required=True)
        parser.add_argument("capacity", type=int, required=True)
        args = parser.parse_args()

        venue = Venues(venue_name=args["name"], venue_location=args["location"], venue_capacity=args["capacity"])
        db.session.add(venue)
        db.session.commit()

        return {"id": venue.venue_id, "name": venue.venue_name, "location": venue.venue_location, "capacity": venue.venue_capacity}, 200

class Search_Venue(Resource):

    def get(self, id=None):
        venues = Venues.query.all()
        if id:
            matched_venues = [venue for venue in venues if id.lower() in venue.venue_name.lower()]
        else:
            matched_venues = venues
        return [{"id": venue.venue_id, "name": venue.venue_name, "location": venue.venue_location, "capacity": venue.venue_capacity} for venue in matched_venues]
#----------------------------------------------------------------------------

class Api_Venue(Resource):
    def get(self, id):
        venue = Venues.query.filter_by(venue_id=id).first()
        if venue:
            return {"id": venue.venue_id, "name": venue.venue_name, "location": venue.venue_location, "capacity": venue.venue_capacity}, 200
        else:
            return {"error": "Venue not found"}, 404

    def put(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str, required=True)
        parser.add_argument("location", type=str, required=True)
        parser.add_argument("capacity", type=int, required=True)
        args = parser.parse_args()

        venue = Venues.query.filter_by(venue_id=id).first()
        if venue:
            venue.venue_name = args["name"]
            venue.venue_location = args["location"]
            venue.venue_capacity = args["capacity"]
            db.session.commit()
            return {"id": venue.venue_id, "name": venue.venue_name, "location": venue.venue_location, "capacity": venue.venue_capacity}, 200
        else:
            return {"error": "Venue not found"}, 404

    def delete(self, id):
        venue = Venues.query.filter_by(venue_id=id).first()
        if venue:
            db.session.delete(venue)
            db.session.commit()
            return {"status": "deleted"}, 202
        else:
            return {"error": "Venue not found"}, 404

# Add the resources to the API
api.add_resource(Api_Venues, "/api/venues", "/venues")
api.add_resource(Search_Venue,"/api/venues/search/<string:id>")
api.add_resource(Api_Venue, "/api/venue/<int:id>", "/venue/<int:id>")

