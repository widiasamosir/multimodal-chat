"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import ConfirmDialog from "@/app/components/ConfirmDialog";
import useDocuments from "@/app/hooks/useDocuments";

export default function Home() {
  const { documents, loading, fetchDocuments, deleteDocument, deleting } = useDocuments();
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const confirmDelete = (id: number) => {
    setDeleteId(id);
    setDialogOpen(true);
  };


  const handleDelete = async () => {
    if (deleteId !== null) {
      await deleteDocument(deleteId);
      setDialogOpen(false);
      setDeleteId(null);
    }
  };

  return (
      <div className="px-4 sm:px-0">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">My Documents</h1>
          <Link
              href="/pages/upload"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            Upload New Document
          </Link>
        </div>

        {loading ? (
            <div className="text-center py-12">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
              <p className="mt-2 text-gray-600">Loading documents...</p>
            </div>
        ) : documents.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <p className="text-gray-500">No documents uploaded yet.</p>
              <Link
                  href="/pages/upload"
                  className="mt-4 inline-block text-blue-600 hover:text-blue-700"
              >
                Upload your first document →
              </Link>
            </div>
        ) : (
            <div className="bg-white shadow overflow-hidden sm:rounded-md">
              <ul className="divide-y divide-gray-200">
                {documents.map((doc) => (
                    <li key={doc.id}>
                      <div className="px-4 py-4 flex items-center sm:px-6 hover:bg-gray-50">
                        <div className="min-w-0 flex-1 sm:flex sm:items-center sm:justify-between">
                          <div className="truncate">
                            <div className="flex text-sm">
                              <p className="font-medium text-blue-600 truncate">{doc.filename}</p>
                              <p className="ml-2 flex-shrink-0 font-normal text-gray-500">
                          <span
                              className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                  doc.status === "completed"
                                      ? "bg-green-100 text-green-800"
                                      : doc.status === "processing"
                                          ? "bg-yellow-100 text-yellow-800"
                                          : doc.status === "error"
                                              ? "bg-red-100 text-red-800"
                                              : "bg-gray-100 text-gray-800"
                              }`}
                          >
                            {doc.status}
                          </span>
                              </p>
                            </div>
                            <div className="mt-2 flex text-sm text-gray-500">
                              <p>
                                {doc.total_pages} pages • {doc.text_chunks} chunks • {doc.images} images •{" "}
                                {doc.tables} tables
                              </p>
                            </div>
                          </div>
                        </div>

                        <div className="ml-5 flex-shrink-0 flex space-x-2">
                          <Link href={`/pages/documents/${doc.id}`} className="text-blue-600 hover:text-blue-900">
                            View
                          </Link>
                          <Link href={`/pages/chat?document=${doc.id}`} className="text-green-600 hover:text-green-900">
                            Chat
                          </Link>
                          <button
                              onClick={() => confirmDelete(doc.id)}
                              className="text-red-600 hover:text-red-900"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </li>
                ))}
              </ul>
            </div>
        )}

        <ConfirmDialog
            isOpen={dialogOpen}
            onCancel={() => setDialogOpen(false)}
            onConfirm={handleDelete}
            text="Are you sure you want to delete the document?"
        />
      </div>
  );
}
