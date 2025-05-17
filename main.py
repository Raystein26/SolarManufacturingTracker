from app import app
import routes
import routes_cleanup
from progress_tracker import progress

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
