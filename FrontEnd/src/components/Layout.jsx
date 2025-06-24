import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar.jsx';

function Layout() {
    return (
        <>
            <Navbar />
            <main>
                <Outlet /> {/* Ini akan me-render komponen halaman (HomePage atau DetailPage) */}
            </main>
        </>
    );
}

export default Layout;
