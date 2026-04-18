// PropIQ ImageUpload Component — Multi-image (exterior + interior)
import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

const TAG_COLORS = {
  exterior: { bg: '#EEEDFE', color: '#534AB7', border: '#534AB7' },
  interior: { bg: '#E1F5EE', color: '#0F6E56', border: '#0F6E56' },
};

function SingleDropzone({ label, tag, onAdd, disabled }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: useCallback(
      (files) => { if (files.length > 0) onAdd(files, tag); },
      [onAdd, tag]
    ),
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] },
    maxFiles: 5,
    maxSize: 10 * 1024 * 1024,
    disabled,
  });

  const col = TAG_COLORS[tag];

  return (
    <div
      {...getRootProps()}
      style={{
        flex: 1,
        border: `2px dashed ${isDragActive ? col.border : 'rgba(44,44,42,0.18)'}`,
        borderRadius: 10,
        padding: '14px 10px',
        textAlign: 'center',
        cursor: disabled ? 'not-allowed' : 'pointer',
        background: isDragActive ? col.bg : '#F7F6F2',
        transition: 'all 0.15s',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <input {...getInputProps()} />
      <div style={{ fontSize: 20, marginBottom: 4 }}>{tag === 'exterior' ? '🏠' : '🛋️'}</div>
      <div style={{ fontSize: 11, fontWeight: 600, color: col.color, marginBottom: 2 }}>
        {label}
      </div>
      <div style={{ fontSize: 10, color: '#888780' }}>
        {isDragActive ? 'Drop here...' : 'Click or drag'}
      </div>
    </div>
  );
}

export default function ImageUpload({ onImagesChange, images = [], disabled = false }) {
  const addImages = useCallback(
    (files, tag) => {
      const newEntries = files.map((file) => ({
        file,
        url: URL.createObjectURL(file),
        tag,
      }));
      onImagesChange([...images, ...newEntries]);
    },
    [images, onImagesChange]
  );

  const removeImage = (idx) => {
    const copy = [...images];
    URL.revokeObjectURL(copy[idx].url);
    copy.splice(idx, 1);
    onImagesChange(copy);
  };

  const maxReached = images.length >= 8;

  return (
    <div style={{ padding: '0 20px 16px' }}>
      {/* Header */}
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: '#5F5E5A',
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          marginBottom: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span>
          Property Photos
          <span
            style={{
              color: '#888780',
              fontWeight: 400,
              textTransform: 'none',
              letterSpacing: 0,
              marginLeft: 4,
            }}
          >
            (optional)
          </span>
        </span>
        {images.length > 0 && (
          <span
            style={{
              background: '#EEEDFE',
              color: '#534AB7',
              borderRadius: 20,
              padding: '2px 8px',
              fontSize: 10,
              fontWeight: 600,
            }}
          >
            {images.length} / 8
          </span>
        )}
      </div>

      {!maxReached && (
        <div style={{ display: 'flex', gap: 8, marginBottom: images.length > 0 ? 10 : 0 }}>
          <SingleDropzone label="Exterior" tag="exterior" onAdd={addImages} disabled={disabled} />
          <SingleDropzone label="Interior" tag="interior" onAdd={addImages} disabled={disabled} />
        </div>
      )}

      {/* Preview grid */}
      {images.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 6,
          }}
        >
          {images.map((img, i) => {
            const col = TAG_COLORS[img.tag];
            return (
              <div
                key={i}
                style={{
                  position: 'relative',
                  borderRadius: 8,
                  overflow: 'hidden',
                  border: `1.5px solid ${col.border}`,
                }}
              >
                <img
                  src={img.url}
                  alt={img.tag}
                  style={{ width: '100%', height: 64, objectFit: 'cover', display: 'block' }}
                />
                {/* Tag badge */}
                <div
                  style={{
                    position: 'absolute',
                    top: 3,
                    left: 3,
                    background: col.bg,
                    color: col.color,
                    fontSize: 9,
                    fontWeight: 700,
                    padding: '1px 5px',
                    borderRadius: 4,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}
                >
                  {img.tag}
                </div>
                {/* Remove button */}
                <button
                  onClick={() => removeImage(i)}
                  style={{
                    position: 'absolute',
                    top: 3,
                    right: 3,
                    background: 'rgba(0,0,0,0.55)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '50%',
                    width: 18,
                    height: 18,
                    fontSize: 10,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    lineHeight: 1,
                  }}
                >
                  ×
                </button>
              </div>
            );
          })}
        </div>
      )}

      {maxReached && (
        <div
          style={{
            fontSize: 10,
            color: '#888780',
            textAlign: 'center',
            marginTop: 6,
            padding: '4px 8px',
            background: '#F1EFE8',
            borderRadius: 6,
          }}
        >
          Max 8 images reached. Remove one to add more.
        </div>
      )}

      {images.length > 0 && (
        <div
          style={{
            marginTop: 8,
            fontSize: 10,
            color: '#0F6E56',
            fontWeight: 600,
            textAlign: 'center',
            background: '#E1F5EE',
            borderRadius: 6,
            padding: '4px 0',
          }}
        >
          📷 {images.length} image{images.length > 1 ? 's' : ''} · CV analysis active
        </div>
      )}
    </div>
  );
}