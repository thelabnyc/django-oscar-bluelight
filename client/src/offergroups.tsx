import React = require('react');
import {render} from 'react-dom';
import OfferGroupTable from './offergroups/OfferGroupTable';


const main = function() {
    const elem = document.querySelector('#offergroup-table') as HTMLDivElement;
    const component = (
        <OfferGroupTable />
    );
    render(component, elem);
};

main();
