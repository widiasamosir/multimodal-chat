import { useState, useEffect, useCallback } from "react";
import Document from "@/app/dtos/documentDtos";

export default function useDocuments() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [deleting, setDeleting] = useState(false);

    const fetchDocuments = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch("http://localhost:8000/api/documents");
            const data = await res.json();
            setDocuments(data.documents || []);
        } catch (error) {
            console.error("Error fetching documents:", error);
        } finally {
            setLoading(false);
        }
    }, []);
    const deleteDocument = useCallback(async (id: number) => {
        setDeleting(true);
        try {
            const res = await fetch(`http://localhost:8000/api/documents/${id}`, {
                method: "DELETE",
            });
            if (!res.ok) {
                const errorText = await res.text();
                throw new Error(`Failed to delete document: ${errorText}`);
            }
            // Refresh list after delete
            await fetchDocuments();
        } catch (error) {
            console.error("Error deleting document:", error);
        } finally {
            setDeleting(false);
        }
    }, [fetchDocuments]);


    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);


    return { documents, loading, deleting, fetchDocuments, deleteDocument };
}
