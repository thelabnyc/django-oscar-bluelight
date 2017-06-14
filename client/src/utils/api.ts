import request = require('superagent');


export const listOfferGroups = function(callback?: (err: any, resp: request.Response) => void) {
    return request
        .get('/dashboard/offers/api/offergroups/')
        .set('Accept', 'application/json')
        .end(callback);
};
