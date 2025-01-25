Para depurar comandos enviados peo mixer, abra a url da sua UI, 
ctrl + shift + I para iniciar ferramentas do desenvolvedor
clique em "console"
digite:

oldReceiveMessage2=receiveMessage2;
oldSendMessage=sendMessage;
receiveMessage2 = function(a){
	oldReceiveMessage2(a);
	if(!a.startsWith("VU2^") && !a.startsWith("RTA^")) console.log("<< \""+a+"\"");
}
sendMessage = function(a){
	console.log(">> \""+a+"\"");
	return oldSendMessage(a);
}