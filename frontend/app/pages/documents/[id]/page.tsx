"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import MediaSection from "@/app/components/MediaSection";
import DocumentDetail from "@/app/dtos/documentDtos";

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDocument();
  }, [params.id]);

  const fetchDocument = async () => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/documents/${params.id}`);
      if (!res.ok) throw new Error("Failed to fetch document");
      const data = await res.json();
      setDocument(data);
    } catch (err) {
      console.error("Error fetching document:", err);
      setDocument(null);
    } finally {
      setLoading(false);
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-green-600";
      case "processing":
        return "text-yellow-600";
      case "error":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  if (loading) {
    return (
        <div className="text-center py-12">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-2 text-gray-600">Loading document...</p>
        </div>
    );
  }

  if (!document) {
    return (
        <div className="text-center py-12">
          <p className="text-gray-600">Document not found</p>
          <Link href="/" className="text-blue-600 hover:text-blue-700 mt-4 inline-block">
            Back to documents
          </Link>
        </div>
    );
  }

  return (
      <div className="px-4 sm:px-0">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{document.filename}</h1>
            <p className="text-sm text-gray-500 mt-1">
              Uploaded: {new Date(document.upload_date).toLocaleDateString()}
            </p>
          </div>
          <div className="flex space-x-3">
            <Link
                href={`/pages/chat?document=${document.id}`}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              Chat with Document
            </Link>
            <button
                onClick={() => router.push("/")}
                className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300"
            >
              Back
            </button>
          </div>
        </div>

        {/* Status */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Processing Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <p className={`text-lg font-semibold ${statusColor(document.status)}`}>
                {document.status}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Pages</p>
              <p className="text-lg font-semibold text-gray-900">{document.total_pages}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Text Chunks</p>
              <p className="text-lg font-semibold text-gray-900">{document.text_chunks}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Media</p>
              <p className="text-lg font-semibold text-gray-900">
                {document.images?.length || 0} images, {document.tables?.length || 0} tables
              </p>
            </div>
          </div>
          {document.error_message && (
              <div className="mt-4 p-4 bg-red-50 rounded-lg">
                <p className="text-sm text-red-800">{document.error_message}</p>
              </div>
          )}
        </div>

        {/* Images */}
        {document.images?.length > 0 && (
            <MediaSection title="Extracted Images" items={document.images} type="image" />
        )}

        {/* Tables */}
        {document.tables?.length > 0 && (
            <MediaSection title="Extracted Tables" items={document.tables} type="table" />
        )}
      </div>
  );
}


