
export default interface DocumentDetail {
    id: number;
    filename: string;
    upload_date: string;
    status: string;
    error_message?: string;
    total_pages: number;
    text_chunks: number;
    images: Array<{
        id: number;
        url: string;
        page: number;
        caption?: string;
        width: number;
        height: number;
    }>;
    tables: Array<{
        id: number;
        url: string;
        page: number;
        caption?: string;
        rows: number;
        columns: number;
        data?: any;
    }>;
}

export default interface Message {
    id: number;
    role: string;
    content: string;
    sources?: any[];
    created_at: string;
}


export default interface Document {
    id: number;
    filename: string;
    upload_date: string;
    status: string;
    total_pages: number;
    text_chunks: number;
    images: number;
    tables: number;
}
