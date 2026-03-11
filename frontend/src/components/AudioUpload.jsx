import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadAudio } from '../api/client'

export default function AudioUpload() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef()
  const navigate = useNavigate()

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  const handleFileChange = (e) => {
    const f = e.target.files[0]
    if (f) setFile(f)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return
    setError(null)
    setUploading(true)
    try {
      const call = await uploadAudio(file)
      navigate(`/calls/${call.id}`)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
      setUploading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Upload Audio</h1>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${
            dragOver ? 'border-slate-400 bg-slate-50' : 'border-slate-300 hover:border-slate-400'
          }`}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".wav,.mp3,.m4a,.webm,.ogg,.flac"
            onChange={handleFileChange}
            className="hidden"
          />
          {file ? (
            <div>
              <p className="font-medium">{file.name}</p>
              <p className="text-sm text-slate-500">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
            </div>
          ) : (
            <div>
              <p className="text-slate-500">Drag & drop an audio file here, or click to browse</p>
              <p className="text-xs text-slate-400 mt-1">WAV, MP3, M4A, WebM, OGG, FLAC</p>
            </div>
          )}
        </div>

        {error && (
          <p className="text-red-600 text-sm">{error}</p>
        )}

        <button
          type="submit"
          disabled={!file || uploading}
          className="w-full bg-slate-700 text-white py-2 rounded-lg font-medium hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? 'Uploading...' : 'Upload & Process'}
        </button>
      </form>
    </div>
  )
}
