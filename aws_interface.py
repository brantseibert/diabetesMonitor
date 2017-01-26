'''
/*
 * Copyright 2010-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License").
 * You may not use this file except in compliance with the License.
 * A copy of the License is located at
 *
 *  http://aws.amazon.com/apache2.0
 *
 * or in the "license" file accompanying this file. This file is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License.
 */
 '''

import boto3
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import sys
import logging

def aws_initialize(USERNAME,host="",rootCAPath="",cognitoIdentityPoolID=""):
	# Missing configuration notification
	missingConfiguration = False
	if not host:
		print("Missing '-e' or '--endpoint'")
		missingConfiguration = True
	if not rootCAPath:
		print("Missing '-r' or '--rootCA'")
		missingConfiguration = True
	if not cognitoIdentityPoolID:
		print("Missing '-C' or '--CognitoIdentityPoolID'")
		missingConfiguration = True
	if missingConfiguration:
		exit(2)

	identityPoolID = cognitoIdentityPoolID
	region = host.split('.')[2]
	cognitoIdentityClient = boto3.client('cognito-identity', region_name=region)

	temporaryIdentityId = cognitoIdentityClient.get_id(IdentityPoolId=identityPoolID)
	identityID = temporaryIdentityId["IdentityId"]

	temporaryCredentials = cognitoIdentityClient.get_credentials_for_identity(IdentityId=identityID)

	AccessKeyId = temporaryCredentials["Credentials"]["AccessKeyId"]
	SecretKey = temporaryCredentials["Credentials"]["SecretKey"]
	SessionToken = temporaryCredentials["Credentials"]["SessionToken"]

	# Init AWSIoTMQTTClient
	clientID = USERNAME + " Monitor"
	myAWSIoTMQTTClient = AWSIoTMQTTClient(clientID, useWebsocket=True)

	# AWSIoTMQTTClient configuration
	myAWSIoTMQTTClient.configureEndpoint(host, 443)
	myAWSIoTMQTTClient.configureCredentials(rootCAPath)
	myAWSIoTMQTTClient.configureIAMCredentials(AccessKeyId, SecretKey, SessionToken)
	myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
	myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
	myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
	myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
	myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

	return myAWSIoTMQTTClient