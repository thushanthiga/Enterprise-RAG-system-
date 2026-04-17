import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const Pagination = ({ currentPage, totalPages, onPageChange }) => {
  if (totalPages <= 1) return null;

  const pages = Array.from({ length: totalPages }, (_, i) => i + 1);

  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center', 
      gap: '0.75rem', 
      marginTop: '2.5rem',
      paddingBottom: '1rem'
    }}>
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        style={{
          background: 'rgba(255, 255, 255, 0.05)',
          border: '1px solid var(--border-color)',
          color: currentPage === 1 ? 'rgba(255, 255, 255, 0.2)' : 'white',
          padding: '0.5rem',
          borderRadius: '10px',
          cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          transition: 'all 0.2s'
        }}
      >
        <ChevronLeft size={20} />
      </button>

      <div style={{ display: 'flex', gap: '0.5rem' }}>
        {pages.map(page => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              border: '1px solid',
              borderColor: currentPage === page ? 'var(--accent-color)' : 'var(--border-color)',
              background: currentPage === page ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              color: currentPage === page ? 'var(--accent-color)' : 'var(--text-muted)',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            {page}
          </button>
        ))}
      </div>

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        style={{
          background: 'rgba(255, 255, 255, 0.05)',
          border: '1px solid var(--border-color)',
          color: currentPage === totalPages ? 'rgba(255, 255, 255, 0.2)' : 'white',
          padding: '0.5rem',
          borderRadius: '10px',
          cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          transition: 'all 0.2s'
        }}
      >
        <ChevronRight size={20} />
      </button>
    </div>
  );
};

export default Pagination;
