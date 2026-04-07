import React, { useState, createContext, useContext, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import {
  AppLayout,
  TopNavigation,
  SideNavigation,
  BreadcrumbGroup,
  Flashbar
} from '@cloudscape-design/components';
import '@cloudscape-design/global-styles/index.css';
import { Amplify } from 'aws-amplify';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { amplifyConfig } from './amplify-config';
import { fetchAuthSession, signOut } from 'aws-amplify/auth';
import { APP_CONFIG } from './config/app.config';
import Overview from './pages/Overview';
import CreateResearch from './pages/CreateResearch';
import ResearchDetails from './pages/ResearchDetails';
import ResearchHistory from './pages/ResearchHistory';
import TraceView from './pages/TraceView';
import ResearchReview from './pages/ResearchReview';
import ReviewResults from './pages/ReviewResults';
import Chat from './pages/Chat';
import Settings from './pages/Settings';

// Configure Amplify
Amplify.configure(amplifyConfig);

// Create Auth Context
const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

function AppContent({ user }) {
  const [navigationOpen, setNavigationOpen] = useState(true);
  const [notifications, setNotifications] = useState([]);
  const [userId, setUserId] = useState(null);
  const [userEmail, setUserEmail] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  // Get user ID and email from Cognito
  useEffect(() => {
    const getUserInfo = async () => {
      try {
        const session = await fetchAuthSession();
        const cognitoUserId = session.tokens?.idToken?.payload?.sub;
        const cognitoUserEmail = session.tokens?.idToken?.payload?.email;
        setUserId(cognitoUserId);
        setUserEmail(cognitoUserEmail);
      } catch (error) {
        console.error('Failed to get user info:', error);
      } finally {
        // Mark auth as ready whether successful or not
        setAuthReady(true);
      }
    };
    getUserInfo();
  }, [user]);

  const handleSignOut = async () => {
    try {
      await signOut();
      navigate('/overview');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const addNotification = (notification) => {
    const id = Date.now().toString();
    const fullNotification = {
      ...notification,
      id,
      dismissible: true,
      onDismiss: () => setNotifications(prev => prev.filter(n => n.id !== id))
    };

    setNotifications(prev => [...prev, fullNotification]);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };

  const navigationItems = [
    { type: 'link', text: 'Overview', href: '/overview' },
    { type: 'divider' },
    {
      type: 'section',
      text: 'Research',
      items: [
        { type: 'link', text: 'New Research', href: '/research/create' },
        { type: 'link', text: 'Research History', href: '/research/history' },
        { type: 'link', text: 'Trace View', href: '/research/traces' }
      ]
    },
    { type: 'divider' },
    {
      type: 'section',
      text: 'Analysis',
      items: [
        { type: 'link', text: 'Research Reviews', href: '/analysis/review' },
        { type: 'link', text: 'Research Chat', href: '/analysis/chat' }
      ]
    },
    { type: 'divider' },
    {
      type: 'section',
      text: 'Settings',
      items: [
        { type: 'link', text: 'Configuration', href: '/settings' }
      ]
    }
  ];

  const getBreadcrumbs = () => {
    const baseBreadcrumb = { text: 'Research Agent', href: '/overview' };
    const path = location.pathname;

    if (path === '/overview') {
      return [baseBreadcrumb];
    }
    if (path.startsWith('/research/create')) {
      return [baseBreadcrumb, { text: 'New Research', href: '/research/create' }];
    }
    if (path.startsWith('/research/history')) {
      return [baseBreadcrumb, { text: 'Research History', href: '/research/history' }];
    }
    if (path.startsWith('/research/traces')) {
      return [baseBreadcrumb, { text: 'Trace View', href: '/research/traces' }];
    }
    if (path.startsWith('/research/') && path.includes('/review')) {
      const sessionId = path.split('/')[2];
      return [
        baseBreadcrumb,
        { text: 'Research Details', href: `/research/${sessionId}` },
        { text: 'Review History', href: `/research/${sessionId}/review` }
      ];
    }
    if (path.startsWith('/research/')) {
      const sessionId = path.split('/')[2];
      return [
        baseBreadcrumb,
        { text: 'Research Details', href: `/research/${sessionId}` }
      ];
    }
    if (path.startsWith('/analysis/review')) {
      return [baseBreadcrumb, { text: 'Research Reviews', href: '/analysis/review' }];
    }
    if (path.startsWith('/analysis/chat')) {
      return [baseBreadcrumb, { text: 'Research Chat', href: '/analysis/chat' }];
    }
    if (path === '/settings') {
      return [baseBreadcrumb, { text: 'Configuration', href: '/settings' }];
    }

    return [baseBreadcrumb];
  };

  // Show loading state until auth is ready
  if (!authReady) {
    return (
      <Box textAlign="center" padding="xxl">
        <Spinner size="large" />
        <Box variant="p" padding={{ top: 's' }}>
          Initializing...
        </Box>
      </Box>
    );
  }

  return (
    <AuthContext.Provider value={{ userId, user, authReady }}>
      <TopNavigation
        identity={{
          href: '/overview',
          title: 'Deep Research Agent',
          onFollow: (event) => {
            event.preventDefault();
            navigate('/overview');
          }
        }}
        utilities={[
          {
            type: 'menu-dropdown',
            text: userEmail || user?.signInDetails?.loginId || 'User',
            iconName: 'user-profile',
            items: [
              {
                id: 'profile',
                text: 'Profile',
                disabled: true
              },
              {
                id: 'signout',
                text: 'Sign out'
              }
            ],
            onItemClick: ({ detail }) => {
              if (detail.id === 'signout') {
                handleSignOut();
              }
            }
          }
        ]}
      />

      <AppLayout
        contentType="default"
        breadcrumbs={
          <BreadcrumbGroup
            items={getBreadcrumbs()}
            expandAriaLabel="Show path"
            ariaLabel="Breadcrumbs"
            onFollow={(event) => {
              if (!event.detail.external) {
                event.preventDefault();
                navigate(event.detail.href);
              }
            }}
          />
        }
        navigation={
          <SideNavigation
            activeHref={location.pathname === '/' ? '/overview' : location.pathname}
            header={{
              href: '/overview',
              text: 'Research Agent'
            }}
            items={navigationItems}
            onFollow={(event) => {
              if (!event.detail.external) {
                event.preventDefault();
                navigate(event.detail.href);
              }
            }}
          />
        }
        navigationOpen={navigationOpen}
        onNavigationChange={({ detail }) => setNavigationOpen(detail.open)}
        notifications={notifications.length > 0 && <Flashbar items={notifications} />}
        content={
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/research/create" element={<CreateResearch addNotification={addNotification} />} />
            <Route path="/research/history" element={<ResearchHistory addNotification={addNotification} />} />
            <Route path="/research/traces" element={<TraceView />} />
            <Route path="/research/:sessionId/review" element={<ReviewResults addNotification={addNotification} />} />
            <Route path="/research/:sessionId" element={<ResearchDetails addNotification={addNotification} />} />
            <Route path="/analysis/review" element={<ResearchReview />} />
            <Route path="/analysis/chat" element={<Chat addNotification={addNotification} />} />
            <Route path="/settings" element={<Settings addNotification={addNotification} />} />
          </Routes>
        }
      />
    </AuthContext.Provider>
  );
}

function App() {
  // Check if authentication is enabled
  if (!APP_CONFIG.features.authentication) {
    return (
      <Router>
        <AppContent user={{ username: 'anonymous' }} />
      </Router>
    );
  }

  return (
    <Authenticator
      socialProviders={[]}
      variation="modal"
      hideSignUp={false}
    >
      {({ user }) => (
        <Router>
          <AppContent user={user} />
        </Router>
      )}
    </Authenticator>
  );
}

export default App;
