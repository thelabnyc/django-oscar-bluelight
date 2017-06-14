export interface IVoucher {
    id: number;
    name: string;
    code: string;
    is_active: boolean;
    details_link: string;
}


export interface IOffer {
    id: number;
    name: string;
    priority: number;
    is_available: boolean;
    vouchers: IVoucher[];
    details_link: string;
}


export interface IOfferGroup {
    id: number;
    name: string;
    priority: number;
    offers: IOffer[];
    update_link: string;
    delete_link: string;
}
