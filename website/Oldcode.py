
                
                
                
                
                """FIX THIS VVVVV """
                
                """NO USERS IN EITHER TABLE CAN HAVE THE SAME USERNAME"""
                # Check the username does not already exists
                # If the pre-existing user is a host
                finderHost = findHost(cursor, username)
                # If the pre-existing user is a delegate
                finderDele = findDelegate(cursor, username) # Basic search used here - Array type returned
                # User is not a host or a delegate --> Username does not already exist
                if (finderHost[0] == False) and (finderDele[0] == False):
                    type = "USER NOT FOUND!"
                if type == "USER NOT FOUND!":
                    if len(password) == 0:
                        flash("Please enter a strong password.", category='error')
                    elif len(confirm) == 0:
                        flash("Please re-enter your password.", category='error')
                    elif len(dob) == 0:
                        flash("Please enter a date of birth.", category='error')
                    elif len(email) == 0 or "@" not in email:
                        flash("Please enter a valid email.", category='error')
                    else:
                        passwdHash = generate_password_hash(password, method="sha256")
                        if check_password_hash(passwdHash, confirm) == False:
                            flash("Please enter matching passwords.", category="error")
                        else:
                            if email != "" or "@" not in email:
                                emailAddr = "None"
                            else:
                                emailAddr = email
                                
                            # Add user to database.
                            if usertype == 'delegate': 
                                addDelegate(cursor, username, passwdHash, dob, emailAddr)
                                
                            else:
                                addHost(cursor, username, passwdHash, dob, emailAddr)
                            idUsed = cursor.lastrowid
                            userinfo = [username, passwdHash, email, idUsed]
                            try:
                                conn.commit()
                                cursor.close()
                                conn.close()
                                flash("Successfully signed up!", category='success')
                                UpdateLog(f"New User: {username} added to the system.")
                                sessionUsr = User(userinfo, idUsed, usertype)
                                login_user(sessionUsr, remember=True) # Create session for user
                                return redirect(url_for("views.home"))
                            except Exception as e:
                                flash(f"Error registering account: {e}", category='error')
                else:
                    
                    
                    
                    type = "host"
        try:
            # If the logging in user is a host
            finder = findHost(cursor, username)
            if finder[0]:
                user = finder[1]
            else: # User is not a host
                type = "delegate"
        except Exception as e:
            UpdateLog(f"(1) SQL ERROR: {e}")
            type = "delegate"
        # If the logging in user is a delegate
        if type == "delegate":
            try:
                # Basic search used here - Array type returned
                finder = findDelegate(cursor, username)
                if finder[0]:
                    user = finder[1]
                else: # User is not a delegate
                    type = "USER NOT FOUND!"
            except Exception as e:
                UpdateLog(f"(2) SQL ERROR: {e}")
                # Otherwise the user seeminly does not exist
                type = "USER NOT FOUND!"